"""
XGBoost CVS Risk Score training pipeline.

Steps:
  1. Load synthetic dataset from parquet.
  2. Stratified 80/20 train-test split (random_state=42).
  3. 5-Fold StratifiedKFold CV on training set.
  4. Final retrain on full training set.
  5. Evaluate on test set: F1 (macro), AUC-ROC, Precision, Recall.
  6. Assert SLOs: F1 >= 0.75 AND AUC-ROC >= 0.80.
  7. Serialize model with joblib + export model_metadata.json.

Target SLOs (paper Table 11):
  - F1-score (macro) >= 0.75
  - AUC-ROC >= 0.80
"""
from __future__ import annotations
import json
import time
import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.metrics import (
    f1_score, roc_auc_score, precision_score, recall_score,
    classification_report, confusion_matrix,
)
from xgboost import XGBClassifier

DATA_PATH = Path(__file__).parent / "data" / "synthetic_dataset.parquet"
RESULTS_DIR = Path(__file__).parent / "results"
MODEL_PATH = RESULTS_DIR / "model.joblib"
METADATA_PATH = RESULTS_DIR / "model_metadata.json"

FEATURE_NAMES = [
    "mean_lux_daily", "std_lux_daily", "mean_proximity_cm", "min_proximity_cm",
    "total_screen_min", "max_cont_session_min", "lux_screen_ratio",
    "evening_screen_ratio", "break_compliance_score",
]

F1_SLO: float = 0.75
AUC_SLO: float = 0.80


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_parquet(DATA_PATH)
    X, y = df[FEATURE_NAMES].values, df["label"].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    neg, pos = (y_train == 0).sum(), (y_train == 1).sum()
    scale_pos_weight = neg / pos

    base_params = dict(
        n_estimators=200, max_depth=6, learning_rate=0.1,
        subsample=0.8, colsample_bytree=0.8,
        scale_pos_weight=scale_pos_weight,
        use_label_encoder=False, eval_metric="logloss", random_state=42,
    )

    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_f1, cv_auc = [], []

    for fold, (tr_idx, val_idx) in enumerate(skf.split(X_train, y_train), 1):
        clf = XGBClassifier(**base_params)
        clf.fit(X_train[tr_idx], y_train[tr_idx])
        preds = clf.predict(X_train[val_idx])
        proba = clf.predict_proba(X_train[val_idx])[:, 1]
        cv_f1.append(f1_score(y_train[val_idx], preds, average="macro"))
        cv_auc.append(roc_auc_score(y_train[val_idx], proba))
        print(f"Fold {fold}: F1={cv_f1[-1]:.4f}  AUC={cv_auc[-1]:.4f}")

    print(f"\nCV F1:  {np.mean(cv_f1):.4f} ± {np.std(cv_f1):.4f}")
    print(f"CV AUC: {np.mean(cv_auc):.4f} ± {np.std(cv_auc):.4f}")

    # Final model on full training set
    final_model = XGBClassifier(**base_params)
    final_model.fit(X_train, y_train)

    test_preds = final_model.predict(X_test)
    test_proba = final_model.predict_proba(X_test)[:, 1]
    test_f1 = f1_score(y_test, test_preds, average="macro")
    test_auc = roc_auc_score(y_test, test_proba)

    print("\n=== TEST SET RESULTS ===")
    print(classification_report(y_test, test_preds, target_names=["Low Risk", "High Risk"]))
    print(f"Confusion Matrix:\n{confusion_matrix(y_test, test_preds)}")
    print(f"F1 Macro: {test_f1:.4f}  |  AUC-ROC: {test_auc:.4f}")

    # Assert SLOs
    assert test_f1 >= F1_SLO,  f"F1 SLO FAILED: {test_f1:.4f} < {F1_SLO}"
    assert test_auc >= AUC_SLO, f"AUC SLO FAILED: {test_auc:.4f} < {AUC_SLO}"
    print("\n✓ All SLOs passed.")

    # Verify top-3 feature importances contain expected clinical features
    importances = final_model.get_booster().get_score(importance_type="gain")
    top_3 = sorted(importances, key=importances.get, reverse=True)[:3]
    print(f"Top-3 features: {top_3}")
    assert "max_cont_session_min" in top_3 or "break_compliance_score" in top_3, \
        "Expected clinical features not in top-3. Review feature engineering."

    joblib.dump(final_model, MODEL_PATH)
    version = time.strftime("%Y%m%d-%H%M%S")
    metadata = {
        "version": version,
        "f1_score": round(test_f1, 4),
        "auc_roc": round(test_auc, 4),
        "precision": round(precision_score(y_test, test_preds, average="macro"), 4),
        "recall": round(recall_score(y_test, test_preds, average="macro"), 4),
        "trained_at": version,
        "feature_names": FEATURE_NAMES,
        "threshold": 0.70,
        "cv_f1_mean": round(float(np.mean(cv_f1)), 4),
        "cv_f1_std": round(float(np.std(cv_f1)), 4),
        "cv_auc_mean": round(float(np.mean(cv_auc)), 4),
        "cv_auc_std": round(float(np.std(cv_auc)), 4),
    }
    METADATA_PATH.write_text(json.dumps(metadata, indent=2))
    print(f"\nModel saved to {MODEL_PATH}")
    print(f"Metadata saved to {METADATA_PATH}")


if __name__ == "__main__":
    main()
