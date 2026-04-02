"""Tests for normalizer transforms."""
from __future__ import annotations

from normalizer.models import NormalizedBatch, NormalizedReading
from normalizer.normalizer import normalize_batch


def test_normalize_batch_non_negative() -> None:
    batch = NormalizedBatch(
        device_uuid="u1",
        batch_timestamp=1,
        readings=[
            NormalizedReading(sensor_type="AMBIENT_LIGHT", value=-10.0, unit="lux", sampled_at=1),
            NormalizedReading(sensor_type="PROXIMITY", value=15.0, unit="cm", sampled_at=1),
        ],
        app_version="1.0.0",
        consent_hash="h",
    )
    out = normalize_batch(batch)
    assert out.readings[0].value == 0.0
    assert out.readings[1].value == 15.0
