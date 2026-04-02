"""API routes for ingestion and score retrieval."""
from __future__ import annotations
import random
from fastapi import APIRouter, HTTPException
from inference_svc.models import ScoreResponse, TelemetryBatchIn

router = APIRouter(prefix="/v1", tags=["Inference"])
_CACHE: dict[str, ScoreResponse] = {}


@router.post("/telemetry/ingest", status_code=202)
def ingest(batch: TelemetryBatchIn) -> dict[str, str]:
    score = round(random.uniform(0.05, 0.95), 4)
    level = "HIGH" if score >= 0.70 else "MEDIUM" if score >= 0.40 else "LOW"
    _CACHE[batch.device_uuid] = ScoreResponse(uuid=batch.device_uuid, risk_score=score, risk_level=level)
    return {"status": "accepted"}


@router.get("/scores/{uuid}/current", response_model=ScoreResponse)
def get_current_score(uuid: str) -> ScoreResponse:
    if uuid not in _CACHE:
        raise HTTPException(status_code=404, detail="Score not found")
    return _CACHE[uuid]
