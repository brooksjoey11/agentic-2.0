"""Locust load test for agentic-shell orchestrator."""
from locust import HttpUser, between, task


class OrchestratorUser(HttpUser):
    wait_time = between(1, 3)
    host = "http://localhost:8000"

    @task(3)
    def health_check(self):
        self.client.get("/health/")

    @task(1)
    def readiness_check(self):
        self.client.get("/health/ready")
