"""Pydantic models for inference API."""
from __future__ import annotations
from pydantic import BaseModel


class SensorReading(BaseModel):
    sensor_type: str
    value: float
    unit: str
    sampled_at: int


class TelemetryBatchIn(BaseModel):
    device_uuid: str
    batch_timestamp: int
    readings: list[SensorReading]
    app_version: str
    consent_hash: str


class ScoreResponse(BaseModel):
    uuid: str
    risk_score: float
    risk_level: str
