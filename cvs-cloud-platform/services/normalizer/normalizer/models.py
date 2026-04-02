"""Pydantic models for normalized telemetry."""
from __future__ import annotations
from pydantic import BaseModel


class NormalizedReading(BaseModel):
    sensor_type: str
    value: float
    unit: str
    sampled_at: int


class NormalizedBatch(BaseModel):
    device_uuid: str
    batch_timestamp: int
    readings: list[NormalizedReading]
    app_version: str
    consent_hash: str
