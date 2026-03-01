"""Metrics service logic."""
from prometheus_client import Counter, Histogram

REQUEST_COUNT = Counter("request_count_total", "Total request count", ["method", "endpoint"])
REQUEST_LATENCY = Histogram("request_latency_seconds", "Request latency", ["endpoint"])


def record_request(method: str, endpoint: str) -> None:
    REQUEST_COUNT.labels(method=method, endpoint=endpoint).inc()
