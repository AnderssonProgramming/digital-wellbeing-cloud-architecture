"""FastAPI entrypoint for the Rule Engine microservice."""
from __future__ import annotations
import threading
import logging
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Counter
from rule_engine.consumer import build_consumer, run_consumer_loop

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="CVS Rule Engine", version="1.0.0")
Instrumentator().instrument(app).expose(app)

# Custom Prometheus metrics
cvs_rule_violations_total = Counter(
    "cvs_rule_violations_total",
    "Total number of CVS rule threshold violations detected.",
    ["rule_id", "severity"],
)


@app.on_event("startup")
def start_consumer() -> None:
    consumer = build_consumer()
    thread = threading.Thread(target=run_consumer_loop, args=(consumer,), daemon=True)
    thread.start()


@app.get("/v1/health", tags=["Health"])
def health() -> dict:
    """Liveness and readiness probe endpoint."""
    return {"status": "ok", "service": "rule-engine"}
