"""Differential Privacy: Laplace mechanism with configurable epsilon and sensitivity."""
from __future__ import annotations
import numpy as np

# Sensitivity per sensor type (from paper Section XI, ADR-004)
SENSOR_SENSITIVITY: dict[str, float] = {
    "AMBIENT_LIGHT": 500.0,   # lux range
    "PROXIMITY": 100.0,        # cm range
    "SCREEN_TIME": 60.0,       # minutes range
}

DEFAULT_EPSILON: float = 1.0  # Privacy budget (GDPR-compliant per paper ADR-004)


def apply_laplace_noise(
    value: float,
    sensor_type: str,
    epsilon: float = DEFAULT_EPSILON,
) -> float:
    """
    Add Laplace-distributed noise to a sensor reading.

    noise ~ Laplace(0, sensitivity / epsilon)

    Args:
        value: Original sensor reading.
        sensor_type: One of AMBIENT_LIGHT, PROXIMITY, SCREEN_TIME.
        epsilon: Privacy budget. Lower = stronger privacy, more noise.

    Returns:
        Noised float value.
    """
    sensitivity = SENSOR_SENSITIVITY.get(sensor_type, 1.0)
    scale = sensitivity / epsilon
    noise = np.random.laplace(loc=0.0, scale=scale)
    return float(value + noise)
