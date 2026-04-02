"""Domain normalization functions."""
from __future__ import annotations

from normalizer.models import NormalizedBatch, NormalizedReading


def normalize_sensor_value(sensor_type: str, value: float) -> float:
    if sensor_type == "AMBIENT_LIGHT":
        return max(value, 0.0)
    if sensor_type == "PROXIMITY":
        return max(value, 0.0)
    if sensor_type == "SCREEN_TIME":
        return max(value, 0.0)
    return value


def normalize_batch(batch: NormalizedBatch) -> NormalizedBatch:
    readings = [
        NormalizedReading(
            sensor_type=r.sensor_type,
            value=normalize_sensor_value(r.sensor_type, r.value),
            unit=r.unit,
            sampled_at=r.sampled_at,
        )
        for r in batch.readings
    ]
    return NormalizedBatch(
        device_uuid=batch.device_uuid,
        batch_timestamp=batch.batch_timestamp,
        readings=readings,
        app_version=batch.app_version,
        consent_hash=batch.consent_hash,
    )
