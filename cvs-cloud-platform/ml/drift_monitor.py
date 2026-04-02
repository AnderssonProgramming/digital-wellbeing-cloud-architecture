"""
KL-Divergence model drift monitor.

Compares the distribution of CVS Risk Scores over the last 7 days vs the
preceding 7 days. If KL-divergence exceeds the threshold, publishes a
MODEL_DRIFT_DETECTED event to cvs.inference.scores.

Runs every 6 hours as a sidecar or standalone CronJob.
"""
from __future__ import annotations
import logging
import os
import numpy as np
from scipy.special import kl_div

logger = logging.getLogger(__name__)

KL_THRESHOLD: float = 0.15


def compute_kl_divergence(p: np.ndarray, q: np.ndarray, bins: int = 50) -> float:
    """
    Compute KL-divergence D(P || Q) between two score distributions.

    Args:
        p: Array of risk scores from the recent window.
        q: Array of risk scores from the baseline window.
        bins: Number of histogram bins.

    Returns:
        KL-divergence scalar (float).
    """
    eps = 1e-10
    p_hist, _ = np.histogram(p, bins=bins, range=(0, 1), density=True)
    q_hist, _ = np.histogram(q, bins=bins, range=(0, 1), density=True)
    p_hist = p_hist + eps
    q_hist = q_hist + eps
    return float(np.sum(kl_div(p_hist, q_hist)))


def check_drift(
    recent_scores: np.ndarray,
    baseline_scores: np.ndarray,
) -> bool:
    """
    Returns True if drift is detected (KL > KL_THRESHOLD).
    """
    kl = compute_kl_divergence(recent_scores, baseline_scores)
    logger.info("KL-divergence: %.4f (threshold: %.4f)", kl, KL_THRESHOLD)
    return kl > KL_THRESHOLD
