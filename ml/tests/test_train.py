"""Tests for training module constants and configuration."""
from __future__ import annotations

from ml.train import AUC_SLO, F1_SLO, FEATURE_NAMES


def test_training_slos_and_feature_count() -> None:
    assert F1_SLO >= 0.75
    assert AUC_SLO >= 0.80
    assert len(FEATURE_NAMES) == 9
