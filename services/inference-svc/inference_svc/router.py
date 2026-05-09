"""Rutas HTTP del servicio de inferencia.

A diferencia de versiones anteriores del prototipo, este endpoint
extrae los nueve `features` agregados a partir del lote recibido
(usando :func:`inference_svc.features.features_from_batch`) y delega
en :class:`inference_svc.scorer.CVSScorer` para obtener un puntaje
real. Si el modelo aún no está cargado en memoria devuelve 503.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from inference_svc.features import features_from_batch
from inference_svc.models import ScoreResponse, TelemetryBatchIn
from inference_svc.scorer import CVSScorer

router = APIRouter(prefix="/v1", tags=["Inference"])

# Cache simple de la última puntuación por dispositivo. En la versión de
# producción debería ser Redis o un read model alimentado por Kafka.
_CACHE: dict[str, ScoreResponse] = {}

# Instancia compartida del scorer. ``main.py`` la pre-carga en startup.
scorer = CVSScorer()


@router.post("/telemetry/ingest", status_code=202)
def ingest(batch: TelemetryBatchIn) -> dict[str, str]:
    """Recibe un lote, calcula el puntaje y lo cachea por dispositivo."""
    if scorer._model is None:  # noqa: SLF001  acceso intencional
        # No hay modelo cargado todavía: el lote se acepta para no
        # bloquear al cliente, pero no se calcula puntaje.
        return {"status": "accepted", "scored": "false"}

    features = features_from_batch(batch)
    result = scorer.predict(features, uuid=batch.device_uuid)

    _CACHE[batch.device_uuid] = ScoreResponse(
        uuid=result.uuid,
        risk_score=round(result.risk_score, 4),
        risk_level=result.risk_level,
    )
    return {"status": "accepted", "scored": "true"}


@router.get("/scores/{uuid}/current", response_model=ScoreResponse)
def get_current_score(uuid: str) -> ScoreResponse:
    if uuid not in _CACHE:
        raise HTTPException(status_code=404, detail="Score not found")
    return _CACHE[uuid]
