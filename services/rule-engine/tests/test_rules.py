"""Pruebas unitarias de las reglas duras del Rule Engine."""
import time

import pytest

from rule_engine.models import SensorReading, SensorType, TelemetryBatch
from rule_engine.rules import (
    LOW_LUX_THRESHOLD,
    PROXIMITY_CONSECUTIVE_VIOLATIONS,
    PROXIMITY_THRESHOLD_CM,
    SCREEN_TIME_THRESHOLD_MIN,
    evaluate_20_20_20,
    evaluate_lux_mismatch,
    evaluate_proximity_violation,
)


def _make_batch(
    readings: list[tuple[SensorType, float]],
    device_uuid: str = "test-uuid",
) -> TelemetryBatch:
    now = int(time.time() * 1000)
    return TelemetryBatch(
        device_uuid=device_uuid,
        batch_timestamp=now,
        readings=[
            SensorReading(
                sensor_type=st,
                value=v,
                unit="lux" if st == SensorType.AMBIENT_LIGHT else "cm",
                sampled_at=now,
            )
            for st, v in readings
        ],
        app_version="1.0.0",
        consent_hash="abc123",
    )


# ----------------------------- Lux ----------------------------------

class TestLuxMismatch:
    def test_below_threshold_triggers_alert(self) -> None:
        batch = _make_batch([(SensorType.AMBIENT_LIGHT, LOW_LUX_THRESHOLD - 1)])
        alert = evaluate_lux_mismatch(batch)
        assert alert is not None
        assert alert.severity == "MEDIUM"
        assert alert.rule_id == "rule.low-lux"

    def test_above_threshold_no_alert(self) -> None:
        batch = _make_batch([(SensorType.AMBIENT_LIGHT, LOW_LUX_THRESHOLD + 100)])
        assert evaluate_lux_mismatch(batch) is None

    def test_exactly_at_threshold_no_alert(self) -> None:
        batch = _make_batch([(SensorType.AMBIENT_LIGHT, LOW_LUX_THRESHOLD)])
        assert evaluate_lux_mismatch(batch) is None


# ------------------------- 20-20-20 ---------------------------------

class TestScreenTime:
    def test_does_not_trigger_below_threshold(self) -> None:
        batch = _make_batch(
            [(SensorType.SCREEN_TIME, 30.0)], device_uuid="dev-st-1"
        )
        assert evaluate_20_20_20(batch) is None

    def test_triggers_when_accumulator_exceeds_threshold(self) -> None:
        # Dos lotes de 25 minutos suman 50, más que el umbral (45).
        device = "dev-st-2"
        evaluate_20_20_20(
            _make_batch([(SensorType.SCREEN_TIME, 25.0)], device_uuid=device)
        )
        alert = evaluate_20_20_20(
            _make_batch([(SensorType.SCREEN_TIME, 25.0)], device_uuid=device)
        )
        assert alert is not None
        assert alert.severity == "HIGH"
        assert alert.rule_id == "rule.20-20-20"

    def test_zero_value_resets_accumulator(self) -> None:
        device = "dev-st-3"
        evaluate_20_20_20(
            _make_batch([(SensorType.SCREEN_TIME, 30.0)], device_uuid=device)
        )
        # Pausa.
        evaluate_20_20_20(
            _make_batch([(SensorType.SCREEN_TIME, 0.0)], device_uuid=device)
        )
        # Nueva sesión bajo el umbral.
        assert evaluate_20_20_20(
            _make_batch([(SensorType.SCREEN_TIME, 20.0)], device_uuid=device)
        ) is None


# --------------------------- Proximidad -----------------------------

class TestProximity:
    def test_does_not_trigger_with_one_reading(self) -> None:
        state: dict[str, list[float]] = {}
        batch = _make_batch(
            [(SensorType.PROXIMITY, 10.0)], device_uuid="dev-p-1"
        )
        assert evaluate_proximity_violation(batch, state) is None

    def test_triggers_after_consecutive_below_threshold(self) -> None:
        state: dict[str, list[float]] = {}
        device = "dev-p-2"
        for _ in range(PROXIMITY_CONSECUTIVE_VIOLATIONS - 1):
            evaluate_proximity_violation(
                _make_batch(
                    [(SensorType.PROXIMITY, PROXIMITY_THRESHOLD_CM - 5)],
                    device_uuid=device,
                ),
                state,
            )
        alert = evaluate_proximity_violation(
            _make_batch(
                [(SensorType.PROXIMITY, PROXIMITY_THRESHOLD_CM - 5)],
                device_uuid=device,
            ),
            state,
        )
        assert alert is not None
        assert alert.severity == "HIGH"
        assert alert.rule_id == "rule.proximity"

    def test_does_not_trigger_when_one_reading_is_far(self) -> None:
        state: dict[str, list[float]] = {}
        device = "dev-p-3"
        for _ in range(PROXIMITY_CONSECUTIVE_VIOLATIONS - 1):
            evaluate_proximity_violation(
                _make_batch(
                    [(SensorType.PROXIMITY, PROXIMITY_THRESHOLD_CM - 5)],
                    device_uuid=device,
                ),
                state,
            )
        # Una lectura "buena" rompe la racha.
        assert evaluate_proximity_violation(
            _make_batch(
                [(SensorType.PROXIMITY, PROXIMITY_THRESHOLD_CM + 10)],
                device_uuid=device,
            ),
            state,
        ) is None
