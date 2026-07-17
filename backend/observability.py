"""Observability: Prometheus metrics and middleware.


This file contains middleware recording per-request latency and counts. stage_timer
records per-stage latency inside the recommend pipeline so we can see which parts take
the most time for auditing. Logs are emitted as single-line JSON so GCP can parse
the fields properly.
"""

from __future__ import annotations

import json
import logging
import time
from contextlib import contextmanager

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Latency buckets tuned for a fast vector-search service (seconds).
_LATENCY_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests.",
    ["method", "path", "status"],
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds.",
    ["method", "path"],
    buckets=_LATENCY_BUCKETS,
)
STAGE_LATENCY = Histogram(
    "recommend_stage_duration_seconds",
    "Latency of individual /recommend pipeline stages in seconds.",
    ["stage"],
    buckets=_LATENCY_BUCKETS,
)

access_logger = logging.getLogger("catch_a_vibe.access")


@contextmanager
def stage_timer(stage: str):
    """Record how long a pipeline stage takes into STAGE_LATENCY."""
    start = time.perf_counter()
    try:
        yield
    finally:
        STAGE_LATENCY.labels(stage=stage).observe(time.perf_counter() - start)


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Time every request, export metrics, and log a structured access line.

    path uses the raw request path. This app's routes are all static (no path
    parameters), so metric cardinality stays bounded. If parameterized routes are
    added later, switch to the matched route template to avoid a cardinality blow-up.
    """

    async def dispatch(self, request: Request, call_next):
        # Don't measure the scrape endpoint itself.
        if request.url.path == "/metrics":
            return await call_next(request)

        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start

        method = request.method
        path = request.url.path
        status = response.status_code

        REQUEST_COUNT.labels(method=method, path=path, status=status).inc()
        REQUEST_LATENCY.labels(method=method, path=path).observe(duration)

        access_logger.info(
            "request",
            extra={
                "http_method": method,
                "http_path": path,
                "http_status": status,
                "duration_ms": round(duration * 1000, 2),
            },
        )
        return response


def metrics_endpoint() -> Response:
    """Expose metrics in Prometheus text exposition format."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


# Standard LogRecord attributes, so we can pick out the structured `extra` fields.
_RESERVED = set(vars(logging.makeLogRecord({}))) | {"message", "asctime", "taskName"}


class JsonLogFormatter(logging.Formatter):
    """Minimal JSON log formatter (no extra dependencies)."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _RESERVED and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: int = logging.INFO) -> None:
    """Route all logs through a single JSON stdout handler.

    Access logging is handled by PrometheusMiddleware, so uvicorn's own access
    logger is silenced to avoid duplicate lines. uvicorn error/startup logs are
    propagated to the root handler so they come out as JSON.
    """
    handler = logging.StreamHandler()
    handler.setFormatter(JsonLogFormatter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)

    logging.getLogger("uvicorn.access").disabled = True
    for name in ("uvicorn", "uvicorn.error"):
        lg = logging.getLogger(name)
        lg.handlers = []
        lg.propagate = True
