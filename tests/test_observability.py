"""Tests for the observability layer (metrics middleware, stage timer, JSON logs).

These test the middleware on a new, minimal FastAPI app to avoid loading in
large embedding models or instantiating Qdrant clients.
"""

import json
import logging

from fastapi import FastAPI
from prometheus_client import REGISTRY
from starlette.testclient import TestClient

import observability as obs


def _make_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(obs.PrometheusMiddleware)

    @app.get("/ping")
    def ping():
        return {"ok": True}

    @app.get("/metrics")
    def metrics():
        return obs.metrics_endpoint()

    return app


def _sample(metric: str, labels: dict) -> float:
    return REGISTRY.get_sample_value(metric, labels) or 0.0


def test_middleware_counts_and_times_requests():
    client = TestClient(_make_app())
    count_labels = {"method": "GET", "path": "/ping", "status": "200"}
    before = _sample("http_requests_total", count_labels)

    client.get("/ping")

    assert _sample("http_requests_total", count_labels) == before + 1
    assert _sample("http_request_duration_seconds_count",
                   {"method": "GET", "path": "/ping"}) >= 1


def test_metrics_endpoint_is_not_self_measured():
    client = TestClient(_make_app())
    client.get("/metrics")
    # The scrape endpoint must not appear as a measured request.
    assert REGISTRY.get_sample_value(
        "http_requests_total",
        {"method": "GET", "path": "/metrics", "status": "200"},
    ) is None


def test_metrics_endpoint_returns_prometheus_text():
    client = TestClient(_make_app())
    client.get("/ping")
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "http_requests_total" in resp.text


def test_stage_timer_records_an_observation():
    labels = {"stage": "unit-test"}
    before = _sample("recommend_stage_duration_seconds_count", labels)
    with obs.stage_timer("unit-test"):
        pass
    assert _sample("recommend_stage_duration_seconds_count", labels) == before + 1


def test_json_formatter_includes_structured_extras():
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname=__file__, lineno=1,
        msg="request", args=(), exc_info=None,
    )
    record.http_status = 200
    record.duration_ms = 12.5

    out = json.loads(obs.JsonLogFormatter().format(record))

    assert out["message"] == "request"
    assert out["level"] == "INFO"
    assert out["http_status"] == 200
    assert out["duration_ms"] == 12.5
