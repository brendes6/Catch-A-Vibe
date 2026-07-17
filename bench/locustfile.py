"""Locust load test for the /recommend endpoint.

Calls the recommendation API with multiple realistic vibe queries to capture
p50/p95/p99 latency and throughput. Run against a full, populated Qdrant collection
in the backend to ensure accuracy.

    locust -f bench/locustfile.py --host http://localhost:8080

Then open http://localhost:8089 (or use --headless, see README).
"""

import random

from locust import HttpUser, between, task

# A spread of vibes: distinctive (easy), generic (hard), and multi-word.
QUERIES = [
    "late night drive",
    "sad rainy day",
    "high energy workout",
    "chill sunday morning coffee",
    "90s throwback party",
    "focus deep work",
    "summer road trip",
    "heartbreak breakup songs",
    "romantic dinner",
    "gym hype",
    "study lofi",
    "christmas classics",
    "indie coffeehouse",
    "throwback hip hop",
    "acoustic campfire",
    "feel good pop",
]


class RecommendUser(HttpUser):
    # Simulated think time between requests from a single user.
    wait_time = between(0.1, 0.5)

    @task
    def recommend(self):
        payload = {"query": random.choice(QUERIES)}
        # name="/recommend" groups all queries under one row in the stats table.
        self.client.post("/recommend", json=payload, name="/recommend")

    @task(1)
    def health(self):
        self.client.get("/health", name="/health")
