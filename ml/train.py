"""Pipeline de entrenamiento del clasificador XGBoost de riesgo CVS.

Pasos:
  1. Cargar el dataset sintético desde Parquet.
  2. Split estratificado 80/20 (``random_state=42``).
  3. Validación cruzada estratificada de 5 folds sobre el train set.
  4. Reentrenamiento final sobre todo el train set.
  5. Evaluación sobre el test set: F1 (macro), AUC-ROC, precisión, exhaustividad.
  6. Aserción de los SLOs: F1 >= 0,75 AND AUC-ROC >= 0,80.
  7. Serialización con ``joblib`` y exportación de ``model_metadata.json``.

SLOs objetivo (ver paper, sección de atributos de calidad):
  - F1-score (macro) >= 0,75
  - AUC-ROC >= 0,80
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

DATA_DIR = Path(__file__).parent / "data"
DATA_PATH_PARQUET = DATA_DIR / "synthetic_dataset.parquet"
DATA_PATH_CSV = DATA_DIR / "synthetic_dataset.csv"
RESULTS_DIR = Path(__file__).parent / "results"
MODEL_PATH = RESULTS_DIR / "model.joblib"
METADATA_PATH = RESULTS_DIR / "model_metadata.json"


def _load_dataset() -> pd.DataFrame:
    """Carga el dataset desde Parquet si existe, si no desde CSV."""
    if DATA_PATH_PARQUET.exists():
        return pd.read_parquet(DATA_PATH_PARQUET)
    if DATA_PATH_CSV.exists():
        return pd.read_csv(DATA_PATH_CSV)
    raise FileNotFoundError(
        "No se encontró el dataset. Corre primero "
        "'python ml/generate_synthetic_dataset.py'."
    )

FEATURE_NAMES = [
    "mean_lux_daily", "std_lux_daily", "mean_proximity_cm", "min_proximity_cm",
    "total_screen_min", "max_cont_session_min", "lux_screen_ratio",
    "evening_screen_ratio", "break_compliance_score",
]

F1_SLO: float = 0.75
AUC_SLO: float = 0.80


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    df = _load_dataset()
    # Mantener DataFrame en lugar de .values para que XGBoost preserve
    # los nombres reales de las features en el booster (en vez de
    # ``f0..f8``).
    X = df[FEATURE_NAMES]
    y = df["label"].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    neg, pos = (y_train == 0).sum(), (y_train == 1).sum()
    scale_pos_weight = neg / pos

    base_params = dict(
        n_estimators=200, max_depth=6, learning_rate=0.1,
        subsample=0.8, colsample_bytree=0.8,
        scale_pos_weight=scale_pos_weight,
        eval_metric="logloss", random_state=42,
    )

    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_f1, cv_auc = [], []

    X_train_arr = X_train.to_numpy() if hasattr(X_train, "to_numpy") else X_train
    for fold, (tr_idx, val_idx) in enumerate(skf.split(X_train_arr, y_train), 1):
        clf = XGBClassifier(**base_params)
        clf.fit(X_train.iloc[tr_idx], y_train[tr_idx])
        preds = clf.predict(X_train.iloc[val_idx])
        proba = clf.predict_proba(X_train.iloc[val_idx])[:, 1]
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
    print("\n[OK] All SLOs passed.")

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
