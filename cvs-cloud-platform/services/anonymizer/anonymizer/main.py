"""FastAPI entrypoint for Anonymizer."""
from __future__ import annotations
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(title="CVS Anonymizer", version="1.0.0")
Instrumentator().instrument(app).expose(app)


@app.get("/v1/health", tags=["Health"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "anonymizer"}
