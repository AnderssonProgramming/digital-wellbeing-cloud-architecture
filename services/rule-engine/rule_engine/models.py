"""Pydantic models mirroring the TelemetryBatch Avro schema."""
from __future__ import annotations
from enum import Enum
from pydantic import BaseModel


class SensorType(str, Enum):
    AMBIENT_LIGHT = "AMBIENT_LIGHT"
    PROXIMITY = "PROXIMITY"
    SCREEN_TIME = "SCREEN_TIME"


class SensorReading(BaseModel):
    sensor_type: SensorType
    value: float
    unit: str
    sampled_at: int  # epoch millis


class TelemetryBatch(BaseModel):
    device_uuid: str
    batch_timestamp: int  # epoch millis
    readings: list[SensorReading]
    app_version: str
    consent_hash: str


class Alert(BaseModel):
    device_uuid: str
    rule_id: str
    triggered_at: int  # epoch millis
    severity: str  # "HIGH" | "MEDIUM"
    description: str
