"""Pydantic models for anonymization pipeline."""
from __future__ import annotations
from pydantic import BaseModel


class AnonymizedReading(BaseModel):
    sensor_type: str
    value: float
    unit: str
    sampled_at: int


class AnonymizedBatch(BaseModel):
    device_uuid: str
    batch_timestamp: int
    readings: list[AnonymizedReading]
    app_version: str
    consent_hash: str
