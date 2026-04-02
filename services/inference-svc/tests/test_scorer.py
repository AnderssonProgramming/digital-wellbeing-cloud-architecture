"""Unit tests for scorer API."""
from __future__ import annotations

import pytest
from inference_svc.scorer import CVSScorer


def test_predict_without_model_raises() -> None:
    scorer = CVSScorer()
    with pytest.raises(RuntimeError):
        scorer.predict({}, "u1")
