"""Pruebas del módulo de ingeniería de ``features``."""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from feature_engineering import FEATURE_NAMES, build_features  # noqa: E402


def test_build_features_returns_empty_for_empty_input() -> None:
    out = build_features(pd.DataFrame())
    assert out.empty


def test_build_features_emits_one_row_per_user_day() -> None:
    rows = [
        {
            "device_uuid": "a",
            "_time": dt.datetime(2026, 5, 1, 9, 0, tzinfo=dt.timezone.utc),
            "AMBIENT_LIGHT": 400.0,
            "PROXIMITY": 35.0,
            "SCREEN_TIME": 20.0,
        },
        {
            "device_uuid": "a",
            "_time": dt.datetime(2026, 5, 1, 10, 0, tzinfo=dt.timezone.utc),
            "AMBIENT_LIGHT": 500.0,
            "PROXIMITY": 40.0,
            "SCREEN_TIME": 30.0,
        },
    ]
    out = build_features(pd.DataFrame(rows))
    assert len(out) == 1
    for col in FEATURE_NAMES:
        assert col in out.columns


def test_build_features_raises_when_required_columns_missing() -> None:
    df = pd.DataFrame([{"foo": 1}])
    with pytest.raises(ValueError):
        build_features(df)
