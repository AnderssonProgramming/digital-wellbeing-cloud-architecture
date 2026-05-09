"""Construcción de los 9 ``features`` del modelo CVS a partir de un lote.

En la versión madura, los ``features`` se calculan sobre una ventana de
30 días en InfluxDB (ver módulo ``ml/feature_engineering.py``). Acá, en
el camino caliente del endpoint de ingestión, calculamos versiones
``por-lote`` que son una aproximación razonable: es lo que tiene sentido
con la información disponible en ese momento. Cuando el ``inference-svc``
maduro tenga acceso a InfluxDB, esta función se puede reemplazar por una
consulta Flux real sin tocar el ``router``.
"""
from __future__ import annotations

from statistics import mean, pstdev
from typing import Iterable

from inference_svc.models import SensorReading, TelemetryBatchIn

EVENING_HOUR_THRESHOLD = 20  # 8:00 p. m. en hora local


def _values(readings: Iterable[SensorReading], sensor_type: str) -> list[float]:
    return [r.value for r in readings if r.sensor_type == sensor_type]


def _safe_mean(xs: list[float]) -> float:
    return float(mean(xs)) if xs else 0.0


def _safe_std(xs: list[float]) -> float:
    return float(pstdev(xs)) if len(xs) >= 2 else 0.0


def _safe_min(xs: list[float]) -> float:
    return float(min(xs)) if xs else 0.0


def features_from_batch(batch: TelemetryBatchIn) -> dict[str, float]:
    """Devuelve un diccionario con los nueve ``features`` que espera el
    scorer XGBoost. Los nombres coinciden con
    :data:`inference_svc.scorer.FEATURE_NAMES`."""
    lux = _values(batch.readings, "AMBIENT_LIGHT")
    prox = _values(batch.readings, "PROXIMITY")
    screen = _values(batch.readings, "SCREEN_TIME")

    total_screen_min = sum(screen)
    max_cont_session_min = max(screen) if screen else 0.0

    mean_lux = _safe_mean(lux)
    # Asumimos brillo de pantalla "estimado" en lux equivalentes (200 lux),
    # un valor típico para pantallas de oficina.
    estimated_screen_brightness = 200.0
    lux_screen_ratio = (
        mean_lux / estimated_screen_brightness
        if estimated_screen_brightness > 0
        else 0.0
    )

    # Fracción del tiempo de pantalla en horas tarde/noche.
    evening_screen = [
        r.value
        for r in batch.readings
        if r.sensor_type == "SCREEN_TIME"
        and (r.sampled_at // 1000 // 3600) % 24 >= EVENING_HOUR_THRESHOLD
    ]
    evening_screen_ratio = (
        sum(evening_screen) / total_screen_min
        if total_screen_min > 0
        else 0.0
    )

    # Compliance: fracción de bloques de 20 min con al menos un valor 0
    # (que el agente registra cuando hay pausa).
    breaks = sum(1 for v in screen if v <= 0.0)
    blocks = max(1, len(screen))
    break_compliance_score = breaks / blocks

    return {
        "mean_lux_daily": mean_lux,
        "std_lux_daily": _safe_std(lux),
        "mean_proximity_cm": _safe_mean(prox),
        "min_proximity_cm": _safe_min(prox),
        "total_screen_min": float(total_screen_min),
        "max_cont_session_min": float(max_cont_session_min),
        "lux_screen_ratio": float(lux_screen_ratio),
        "evening_screen_ratio": float(evening_screen_ratio),
        "break_compliance_score": float(break_compliance_score),
    }
