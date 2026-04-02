"""
Generate a synthetic behavioral dataset for XGBoost CVS Risk Score training.

Produces 50,000 user-day records calibrated to clinical thresholds from:
  Sheppard & Wolffsohn (2018). BMJ Open Ophthalmology, 3(1), e000146.

Label: y=1 if break_compliance_score < 0.40 AND max_cont_session_min > 45.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from pathlib import Path

RANDOM_SEED: int = 42
N_SAMPLES: int = 50_000
OUTPUT_PATH: Path = Path(__file__).parent / "data" / "synthetic_dataset.parquet"


def generate(n: int = N_SAMPLES, seed: int = RANDOM_SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    mean_lux = np.clip(rng.normal(300, 150, n), 10, 1000)
    std_lux = rng.exponential(50, n)
    mean_prox = np.clip(rng.normal(45, 20, n), 15, 100)
    min_prox = np.clip(mean_prox - rng.uniform(5, 20, n), 5, mean_prox)
    total_screen = np.clip(rng.normal(480, 120, n), 60, 840)
    max_cont = np.clip(rng.uniform(20, np.minimum(total_screen, 180)), 20, 180)
    lux_ratio = mean_lux / 200.0
    evening_ratio = rng.beta(2, 5, n)
    break_score = rng.beta(3, 2, n)

    df = pd.DataFrame({
        "mean_lux_daily": mean_lux,
        "std_lux_daily": std_lux,
        "mean_proximity_cm": mean_prox,
        "min_proximity_cm": min_prox,
        "total_screen_min": total_screen,
        "max_cont_session_min": max_cont,
        "lux_screen_ratio": lux_ratio,
        "evening_screen_ratio": evening_ratio,
        "break_compliance_score": break_score,
    })

    # CVS high-risk label per paper Section VI.E
    df["label"] = (
        (df["break_compliance_score"] < 0.40) &
        (df["max_cont_session_min"] > 45)
    ).astype(int)

    positive_rate = df["label"].mean()
    print(f"Generated {n} samples. Positive rate: {positive_rate:.2%}")
    assert 0.20 <= positive_rate <= 0.50, f"Unexpected positive rate: {positive_rate:.2%}"

    return df


if __name__ == "__main__":
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df = generate()
    df.to_parquet(OUTPUT_PATH, index=False)
    print(f"Dataset saved to {OUTPUT_PATH}")
