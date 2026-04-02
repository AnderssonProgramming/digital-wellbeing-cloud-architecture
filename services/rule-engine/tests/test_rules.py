"""Unit tests for CVS rule evaluation functions."""
import pytest
from rule_engine.models import SensorReading, SensorType, TelemetryBatch
from rule_engine.rules import evaluate_lux_mismatch, LOW_LUX_THRESHOLD
import time


def _make_batch(sensor_type: SensorType, value: float, device_uuid: str = "test-uuid") -> TelemetryBatch:
    return TelemetryBatch(
        device_uuid=device_uuid,
        batch_timestamp=int(time.time() * 1000),
        readings=[SensorReading(
            sensor_type=sensor_type,
            value=value,
            unit="lux",
            sampled_at=int(time.time() * 1000),
        )],
        app_version="1.0.0",
        consent_hash="abc123",
    )


class TestLuxMismatch:
    def test_below_threshold_triggers_alert(self) -> None:
        batch = _make_batch(SensorType.AMBIENT_LIGHT, LOW_LUX_THRESHOLD - 1)
        alert = evaluate_lux_mismatch(batch)
        # TODO: uncomment after implementing evaluate_lux_mismatch
        # assert alert is not None
        # assert alert.severity == "MEDIUM"

    def test_above_threshold_no_alert(self) -> None:
        batch = _make_batch(SensorType.AMBIENT_LIGHT, LOW_LUX_THRESHOLD + 100)
        alert = evaluate_lux_mismatch(batch)
        # TODO: uncomment after implementing evaluate_lux_mismatch
        # assert alert is None

    def test_exactly_at_threshold_no_alert(self) -> None:
        batch = _make_batch(SensorType.AMBIENT_LIGHT, LOW_LUX_THRESHOLD)
        alert = evaluate_lux_mismatch(batch)
        # TODO: uncomment after implementing evaluate_lux_mismatch
        # assert alert is None
