"""Tests for ML feature engineering module."""
from __future__ import annotations

import pandas as pd
import pytest
from ml.feature_engineering import build_features


def test_build_features_not_implemented() -> None:
    with pytest.raises(NotImplementedError):
        build_features(pd.DataFrame())
