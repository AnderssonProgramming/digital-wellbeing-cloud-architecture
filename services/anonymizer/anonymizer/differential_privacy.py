"""Privacidad diferencial: mecanismo de Laplace con epsilon y
sensibilidad configurables por tipo de sensor."""
from __future__ import annotations

import os

import numpy as np

# Sensibilidad por tipo de sensor (rango aproximado de cada lectura).
SENSOR_SENSITIVITY: dict[str, float] = {
    "AMBIENT_LIGHT": 500.0,   # rango en lux
    "PROXIMITY": 100.0,       # rango en cm
    "SCREEN_TIME": 60.0,      # rango en minutos
}

DEFAULT_EPSILON: float = 1.0  # Presupuesto de privacidad (ver paper, sección IX-B).

# En producción la semilla se deja sin fijar a propósito: una secuencia
# determinista volvería predecible el ruido y rompería la garantía de
# privacidad. Solo cuando ``DP_SEED`` está en el entorno (entorno de
# pruebas) usamos una semilla concreta.
_seed_env = os.environ.get("DP_SEED")
_rng: np.random.Generator = np.random.default_rng(
    int(_seed_env) if _seed_env is not None else None
)


def apply_laplace_noise(
    value: float,
    sensor_type: str,
    epsilon: float = DEFAULT_EPSILON,
) -> float:
    """Añade ruido Laplace(0, sensibilidad / epsilon) a una lectura.

    Args:
        value: lectura cruda del sensor.
        sensor_type: ``AMBIENT_LIGHT``, ``PROXIMITY`` o ``SCREEN_TIME``.
        epsilon: presupuesto de privacidad. Más pequeño = más privacidad
            y más ruido.

    Returns:
        El valor con ruido como ``float``.
    """
    sensitivity = SENSOR_SENSITIVITY.get(sensor_type, 1.0)
    scale = sensitivity / epsilon
    noise = _rng.laplace(loc=0.0, scale=scale)
    return float(value + noise)
