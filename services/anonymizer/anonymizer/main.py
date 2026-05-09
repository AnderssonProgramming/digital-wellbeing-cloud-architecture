"""Punto de entrada FastAPI del servicio Anonymizer."""
from __future__ import annotations

import logging
import threading

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from anonymizer.consumer import build_consumer, run_consumer_loop

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="CVS Anonymizer", version="1.0.0")
Instrumentator().instrument(app).expose(app)


@app.on_event("startup")
def _start_consumer() -> None:
    consumer = build_consumer()
    thread = threading.Thread(
        target=run_consumer_loop, args=(consumer,), daemon=True
    )
    thread.start()
    logger.info("Hilo del consumidor Kafka arrancado.")


@app.get("/v1/health", tags=["Health"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "anonymizer"}
