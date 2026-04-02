"""FastAPI entrypoint for inference service."""
from __future__ import annotations
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from inference_svc.router import router

app = FastAPI(title="CVS Inference Service", version="1.0.0")
Instrumentator().instrument(app).expose(app)
app.include_router(router)


@app.get("/v1/health", tags=["Health"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "inference-svc"}
