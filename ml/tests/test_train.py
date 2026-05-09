"""Pruebas de las constantes y la configuración del módulo de entrenamiento."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from train import AUC_SLO, F1_SLO, FEATURE_NAMES  # noqa: E402


def test_training_slos_and_feature_count() -> None:
    assert F1_SLO >= 0.75
    assert AUC_SLO >= 0.80
    assert len(FEATURE_NAMES) == 9
