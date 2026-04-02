"""Tests for anonymizer primitives."""
from __future__ import annotations

from anonymizer.differential_privacy import apply_laplace_noise
from anonymizer.pseudonymizer import pseudonymize_device_uuid


def test_pseudonymization_is_deterministic() -> None:
    p1 = pseudonymize_device_uuid("abc", "secret")
    p2 = pseudonymize_device_uuid("abc", "secret")
    assert p1 == p2
    assert len(p1) == 32


def test_apply_laplace_noise_returns_float() -> None:
    value = apply_laplace_noise(100.0, "AMBIENT_LIGHT", epsilon=1.0)
    assert isinstance(value, float)
