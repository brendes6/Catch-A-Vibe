# Load testing

A small load test for `/recommend`, used as a basic quality check that the
service stays responsive under concurrent traffic (latency + throughput). It's
a sanity tool that ships with the repo, not the centerpiece of the project.

## Prerequisites

The benchmark is only meaningful against a populated Qdrant collection — an
empty collection returns instantly and tells you nothing. Bring up the local
stack and load a subset of the dataset first.

```bash
# 1. Start the API + Qdrant locally
docker compose up -d --build

# 2. Populate Qdrant with a subset of the MPD (adjust max_slices for size/speed).
#    Point the pipeline at the local Qdrant and run it. From data-processing/:
QDRANT_URL=http://localhost:6333 python process_data.py   # uses ./mpd-dataset

# 3. Confirm the API is up and the collection is populated
curl -s localhost:8080/health
```

> The pipeline reads slices from `data-processing/mpd-dataset/`. Use a handful of
> slices for a quick run; use more for a scale test. Record how many playlists /
> songs you loaded so the benchmark is reproducible.

## Install

```bash
pip install -r bench/requirements.txt
```

## Run

Interactive UI (open http://localhost:8089):

```bash
locust -f bench/locustfile.py --host http://localhost:8080
```

Headless, fixed load (10 users, spawn 2/s, 60s) — good for a repeatable number:

```bash
locust -f bench/locustfile.py --host http://localhost:8080 \
  --headless -u 10 -r 2 -t 60s --csv bench/results/before
```

The `--csv` flag writes `*_stats.csv` with p50/p95/p99 and RPS if you want to
keep a record of a run.

## Reading the results

- **p50 / p95 / p99** — latency percentiles (ms). p95/p99 is what users feel.
- **RPS** — requests/sec sustained (throughput).
- Cross-check against `/metrics`:
  - `http_request_duration_seconds` — request latency histogram.
  - `recommend_stage_duration_seconds{stage="embed|retrieve|rank"}` — where the
    time goes across the pipeline stages.

```bash
curl -s localhost:8080/metrics | grep recommend_stage_duration_seconds
```
