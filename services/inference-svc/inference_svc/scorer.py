"""XGBoost model loading, caching, and CVS Risk Score inference."""
from __future__ import annotations
import logging
import os
import joblib
import numpy as np
from dataclasses import dataclass

logger = logging.getLogger(__name__)

RISK_THRESHOLD: float = 0.70  # Score above this triggers an alert

FEATURE_NAMES: list[str] = [
    "mean_lux_daily",
    "std_lux_daily",
    "mean_proximity_cm",
    "min_proximity_cm",
    "total_screen_min",
    "max_cont_session_min",
    "lux_screen_ratio",
    "evening_screen_ratio",
    "break_compliance_score",
]


@dataclass
class RiskScoreResult:
    uuid: str
    risk_score: float
    risk_level: str          # "LOW" | "MEDIUM" | "HIGH"
    top_3_features: list[str]
    model_version: str
    model_stale: bool


class CVSScorer:
    """
    Loads an XGBoost model from disk and performs CVS Risk Score inference.
    Implements stale model cache: if S3 is unreachable, serves the last
    successfully loaded model with model_stale=True flag.
    """

    def __init__(self) -> None:
        self._model = None
        self._model_version: str = "none"
        self._model_stale: bool = False

    def load_model(self, model_path: str, version: str) -> None:
        """Load a serialized XGBoost model from local path (previously downloaded from S3)."""
        self._model = joblib.load(model_path)
        self._model_version = version
        self._model_stale = False
        logger.info("Loaded model version %s from %s", version, model_path)

    def mark_stale(self) -> None:
        """Mark current model as stale (S3 unavailable during refresh)."""
        self._model_stale = True

    def predict(self, features: dict[str, float], uuid: str) -> RiskScoreResult:
        """
        Run inference on a 9-feature vector and return a RiskScoreResult.

        Args:
            features: Dict mapping FEATURE_NAMES to float values.
            uuid: Pseudonymous device identifier.

        Returns:
            RiskScoreResult with score, level, and top-3 contributing features.
        """
        if self._model is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        # Build feature vector in the correct order
        X = np.array([[features.get(f, 0.0) for f in FEATURE_NAMES]])
        score = float(self._model.predict_proba(X)[0][1])

        if score >= RISK_THRESHOLD:
            level = "HIGH"
        elif score >= 0.40:
            level = "MEDIUM"
        else:
            level = "LOW"

        # Feature importance from booster
        importances = self._model.get_booster().get_score(importance_type="gain")
        top_3 = sorted(importances, key=importances.get, reverse=True)[:3]

        return RiskScoreResult(
            uuid=uuid,
            risk_score=score,
            risk_level=level,
            top_3_features=top_3,
            model_version=self._model_version,
            model_stale=self._model_stale,
        )
