"""Punto de entrada FastAPI del servicio de inferencia."""
from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from inference_svc.router import router, scorer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="CVS Inference Service", version="1.0.0")
Instrumentator().instrument(app).expose(app)
app.include_router(router)


@app.on_event("startup")
def _load_model() -> None:
    """Carga el modelo XGBoost al arranque si la ruta existe.

    En producción la ruta apunta a un volumen montado por el sidecar
    ``model-fetcher`` que sincroniza el artefacto desde S3. Si la ruta
    no existe (caso típico en pruebas locales) se deja el scorer sin
    modelo: el endpoint responde 202 sin scoring hasta que el modelo
    aparezca.
    """
    model_path = os.environ.get("MODEL_PATH", "/models/cvs_model.joblib")
    model_version = os.environ.get("MODEL_VERSION", "dev-local")
    if not Path(model_path).exists():
        logger.warning(
            "MODEL_PATH=%s no existe; el scorer arranca sin modelo.",
            model_path,
        )
        return
    try:
        scorer.load_model(model_path, model_version)
        logger.info("Modelo %s cargado desde %s", model_version, model_path)
    except (OSError, RuntimeError) as exc:
        logger.error("Error cargando modelo: %s", exc)


@app.get("/v1/health", tags=["Health"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "inference-svc"}
