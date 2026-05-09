"""Reglas duras de CVS: 20-20-20, proximidad sostenida, baja luz ambiente."""
from __future__ import annotations
import time
from rule_engine.models import Alert, SensorReading, SensorType, TelemetryBatch

SCREEN_TIME_THRESHOLD_MIN: float = 45.0
PROXIMITY_THRESHOLD_CM: float = 20.0
PROXIMITY_CONSECUTIVE_VIOLATIONS: int = 5
LOW_LUX_THRESHOLD: float = 50.0

# Estado en memoria del acumulador de tiempo activo por dispositivo.
# Clave: device_uuid. Valor: minutos acumulados desde la última pausa.
_screen_time_accumulator: dict[str, float] = {}


def _now_ms() -> int:
    return int(time.time() * 1000)


def evaluate_20_20_20(batch: TelemetryBatch) -> Alert | None:
    """Evalúa la regla 20-20-20 sobre el lote.

    Acumula el ``value`` (en minutos) de cada lectura SCREEN_TIME por
    dispositivo. Una lectura con ``value == 0`` se interpreta como una
    pausa y resetea el acumulador. Cuando el acumulador supera el umbral
    devuelve una alerta de severidad HIGH.
    """
    accum = _screen_time_accumulator.get(batch.device_uuid, 0.0)
    for reading in batch.readings:
        if reading.sensor_type != SensorType.SCREEN_TIME:
            continue
        if reading.value <= 0.0:
            accum = 0.0
        else:
            accum += float(reading.value)

    _screen_time_accumulator[batch.device_uuid] = accum

    if accum > SCREEN_TIME_THRESHOLD_MIN:
        # Reseteamos para no spamear: una sola alerta por cruce.
        _screen_time_accumulator[batch.device_uuid] = 0.0
        return Alert(
            device_uuid=batch.device_uuid,
            rule_id="rule.20-20-20",
            triggered_at=_now_ms(),
            severity="HIGH",
            description=(
                f"Sesión continua de {accum:.1f} min sin pausa "
                f"(umbral {SCREEN_TIME_THRESHOLD_MIN:.0f})."
            ),
        )
    return None


def evaluate_proximity_violation(
    batch: TelemetryBatch,
    consecutive_window: dict[str, list[float]],
) -> Alert | None:
    """Alerta si la distancia al rostro queda por debajo del umbral
    durante ``PROXIMITY_CONSECUTIVE_VIOLATIONS`` lecturas seguidas.

    ``consecutive_window`` es un diccionario compartido entre llamadas
    que el invocador mantiene vivo. Permite ventana deslizante sin
    estado global del módulo.
    """
    window = consecutive_window.setdefault(batch.device_uuid, [])
    for reading in batch.readings:
        if reading.sensor_type != SensorType.PROXIMITY:
            continue
        window.append(float(reading.value))
        # Recortar a las últimas N lecturas para acotar la memoria.
        if len(window) > PROXIMITY_CONSECUTIVE_VIOLATIONS:
            del window[0:-PROXIMITY_CONSECUTIVE_VIOLATIONS]

    if len(window) >= PROXIMITY_CONSECUTIVE_VIOLATIONS and all(
        v < PROXIMITY_THRESHOLD_CM for v in window[-PROXIMITY_CONSECUTIVE_VIOLATIONS:]
    ):
        # Vaciamos para no repetir la misma alerta inmediatamente.
        consecutive_window[batch.device_uuid] = []
        return Alert(
            device_uuid=batch.device_uuid,
            rule_id="rule.proximity",
            triggered_at=_now_ms(),
            severity="HIGH",
            description=(
                f"Distancia al rostro por debajo de "
                f"{PROXIMITY_THRESHOLD_CM:.0f} cm durante "
                f"{PROXIMITY_CONSECUTIVE_VIOLATIONS} lecturas seguidas."
            ),
        )
    return None


def evaluate_lux_mismatch(batch: TelemetryBatch) -> Alert | None:
    """Alerta si alguna lectura de luz ambiente del lote queda por
    debajo del umbral mínimo. Severidad MEDIUM (no es urgente,
    pero el área debería corregir la iluminación)."""
    for reading in batch.readings:
        if reading.sensor_type != SensorType.AMBIENT_LIGHT:
            continue
        if reading.value < LOW_LUX_THRESHOLD:
            return Alert(
                device_uuid=batch.device_uuid,
                rule_id="rule.low-lux",
                triggered_at=_now_ms(),
                severity="MEDIUM",
                description=(
                    f"Luz ambiente {reading.value:.0f} lux por debajo "
                    f"del mínimo recomendado ({LOW_LUX_THRESHOLD:.0f})."
                ),
            )
    return None
