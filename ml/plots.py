"""Genera las gráficas del paper a partir del modelo y dataset entrenados.

Salidas (PDF, ``paper/figures/``):

  - ``roc_curve.pdf``         curva ROC con AUC anotada
  - ``feature_importance.pdf`` importancias por ganancia (gain)
  - ``score_distribution.pdf`` distribución del puntaje por clase real
  - ``dataset_overview.pdf``   histogramas de las 9 features
  - ``confusion_matrix.pdf``   matriz de confusión normalizada

Cómo regenerarlas
-----------------

    python ml/generate_synthetic_dataset.py
    python ml/train.py
    python ml/plots.py

Si ``model.joblib`` no existe el script se queja con un mensaje claro.
"""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import (
    auc,
    confusion_matrix,
    precision_recall_curve,
    roc_curve,
)
from sklearn.model_selection import train_test_split

# ----- rutas ----------------------------------------------------------
HERE = Path(__file__).parent
RESULTS_DIR = HERE / "results"
DATA_DIR = HERE / "data"
FIGURES_DIR = HERE.parent / "paper" / "figures"

MODEL_PATH = RESULTS_DIR / "model.joblib"
METADATA_PATH = RESULTS_DIR / "model_metadata.json"
PARQUET_PATH = DATA_DIR / "synthetic_dataset.parquet"
CSV_PATH = DATA_DIR / "synthetic_dataset.csv"

# ----- estética -------------------------------------------------------
plt.rcParams.update(
    {
        "font.family": "serif",
        "font.size": 10,
        "axes.labelsize": 10,
        "axes.titlesize": 11,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.alpha": 0.25,
        "grid.linestyle": "--",
        "savefig.bbox": "tight",
        "savefig.dpi": 200,
    }
)

FEATURE_NAMES = [
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

# ----- helpers --------------------------------------------------------


def _load_dataset() -> pd.DataFrame:
    if PARQUET_PATH.exists():
        return pd.read_parquet(PARQUET_PATH)
    if CSV_PATH.exists():
        return pd.read_csv(CSV_PATH)
    raise FileNotFoundError(
        "No se encontró el dataset. Corre primero "
        "'python ml/generate_synthetic_dataset.py'."
    )


def _require_model() -> tuple[object, dict]:
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            "No hay modelo entrenado. Corre primero 'python ml/train.py'."
        )
    model = joblib.load(MODEL_PATH)
    metadata = json.loads(METADATA_PATH.read_text()) if METADATA_PATH.exists() else {}
    return model, metadata


def _split() -> tuple[pd.DataFrame, pd.DataFrame, np.ndarray, np.ndarray]:
    df = _load_dataset()
    X = df[FEATURE_NAMES]
    y = df["label"].to_numpy()
    return train_test_split(X, y, test_size=0.20, random_state=42, stratify=y)


def _save(fig: plt.Figure, name: str) -> Path:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    out = FIGURES_DIR / name
    fig.savefig(out)
    plt.close(fig)
    print(f"  -> {out.relative_to(HERE.parent)}")
    return out


# ----- plots ----------------------------------------------------------


def plot_roc(model, X_test, y_test) -> Path:
    proba = model.predict_proba(X_test)[:, 1]
    fpr, tpr, _ = roc_curve(y_test, proba)
    auc_value = auc(fpr, tpr)

    prec, rec, _ = precision_recall_curve(y_test, proba)
    pr_auc = auc(rec, prec)

    fig, axes = plt.subplots(1, 2, figsize=(7.5, 3.4))

    axes[0].plot(fpr, tpr, color="#1f77b4", lw=2, label=f"AUC = {auc_value:.3f}")
    axes[0].plot([0, 1], [0, 1], color="gray", lw=1, linestyle=":")
    axes[0].fill_between(fpr, tpr, alpha=0.10, color="#1f77b4")
    axes[0].set_xlabel("Tasa de falsos positivos")
    axes[0].set_ylabel("Tasa de verdaderos positivos")
    axes[0].set_title("Curva ROC")
    axes[0].legend(loc="lower right", frameon=False)
    axes[0].set_xlim(0, 1)
    axes[0].set_ylim(0, 1.02)

    axes[1].plot(rec, prec, color="#d62728", lw=2, label=f"AP = {pr_auc:.3f}")
    axes[1].fill_between(rec, prec, alpha=0.10, color="#d62728")
    axes[1].set_xlabel("Exhaustividad (recall)")
    axes[1].set_ylabel("Precisión")
    axes[1].set_title("Curva Precisión-Exhaustividad")
    axes[1].legend(loc="lower left", frameon=False)
    axes[1].set_xlim(0, 1)
    axes[1].set_ylim(0, 1.02)

    fig.tight_layout()
    return _save(fig, "roc_curve.pdf")


def plot_feature_importance(model) -> Path:
    booster = model.get_booster()
    raw = booster.get_score(importance_type="gain")
    # Asegurar que todas las features aparezcan, aun con gain=0.
    items = [(name, raw.get(name, 0.0)) for name in FEATURE_NAMES]
    items.sort(key=lambda kv: kv[1])
    names, gains = zip(*items)

    # Normalizamos para que el lector compare proporciones.
    total = sum(gains) or 1.0
    proportions = np.array(gains) / total

    colors = plt.cm.viridis(np.linspace(0.25, 0.85, len(names)))

    fig, ax = plt.subplots(figsize=(6.5, 3.6))
    bars = ax.barh(names, proportions, color=colors, edgecolor="black", linewidth=0.4)
    for bar, value in zip(bars, proportions):
        ax.text(
            value + 0.005,
            bar.get_y() + bar.get_height() / 2,
            f"{value:.2f}",
            va="center",
            fontsize=8.5,
        )
    ax.set_xlabel("Importancia normalizada por ganancia")
    ax.set_title("Importancia de cada feature en XGBoost")
    ax.set_xlim(0, max(proportions) * 1.18)
    fig.tight_layout()
    return _save(fig, "feature_importance.pdf")


def plot_score_distribution(model, X_test, y_test) -> Path:
    proba = model.predict_proba(X_test)[:, 1]
    bins = np.linspace(0, 1, 41)

    fig, ax = plt.subplots(figsize=(6.5, 3.4))
    ax.hist(
        proba[y_test == 0],
        bins=bins,
        alpha=0.55,
        label="Etiqueta = bajo riesgo",
        color="#2ca02c",
        edgecolor="black",
        linewidth=0.3,
    )
    ax.hist(
        proba[y_test == 1],
        bins=bins,
        alpha=0.55,
        label="Etiqueta = alto riesgo",
        color="#d62728",
        edgecolor="black",
        linewidth=0.3,
    )
    ax.axvline(
        0.70,
        color="black",
        linestyle="--",
        lw=1,
        label="Umbral de alerta = 0,70",
    )
    ax.set_xlabel("Puntaje de riesgo CVS")
    ax.set_ylabel("Cantidad de registros (test set)")
    ax.set_title("Distribución del puntaje por clase real")
    ax.legend(frameon=False, loc="upper center")
    fig.tight_layout()
    return _save(fig, "score_distribution.pdf")


def plot_dataset_overview() -> Path:
    df = _load_dataset()
    fig, axes = plt.subplots(3, 3, figsize=(8.5, 7.0))
    palette = plt.cm.tab10(np.linspace(0, 1, len(FEATURE_NAMES)))

    for ax, name, color in zip(axes.ravel(), FEATURE_NAMES, palette):
        values = df[name].to_numpy()
        ax.hist(values, bins=40, color=color, alpha=0.75, edgecolor="black", linewidth=0.3)
        ax.set_title(name, fontsize=9)
        ax.tick_params(labelsize=8)

    fig.suptitle("Distribución de las 9 features sobre 50 000 registros", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    return _save(fig, "dataset_overview.pdf")


def plot_confusion_matrix(model, X_test, y_test) -> Path:
    preds = model.predict(X_test)
    cm = confusion_matrix(y_test, preds)
    cm_norm = cm.astype("float") / cm.sum(axis=1, keepdims=True)

    fig, ax = plt.subplots(figsize=(4.0, 3.4))
    im = ax.imshow(cm_norm, cmap="Blues", vmin=0, vmax=1)
    ax.set_xticks([0, 1])
    ax.set_yticks([0, 1])
    ax.set_xticklabels(["Bajo riesgo", "Alto riesgo"])
    ax.set_yticklabels(["Bajo riesgo", "Alto riesgo"])
    ax.set_xlabel("Clase predicha")
    ax.set_ylabel("Clase real")
    ax.set_title("Matriz de confusión normalizada")
    ax.grid(False)

    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            txt = f"{cm[i, j]}\n({cm_norm[i, j]*100:.1f} %)"
            color = "white" if cm_norm[i, j] > 0.5 else "black"
            ax.text(j, i, txt, ha="center", va="center", color=color, fontsize=9)

    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    return _save(fig, "confusion_matrix.pdf")


# ----- main -----------------------------------------------------------


def main() -> None:
    model, metadata = _require_model()
    _, X_test, _, y_test = _split()

    print("Generando figuras en paper/figures/")
    plot_roc(model, X_test, y_test)
    plot_feature_importance(model)
    plot_score_distribution(model, X_test, y_test)
    plot_dataset_overview()
    plot_confusion_matrix(model, X_test, y_test)

    if metadata:
        print(
            f"Resumen del modelo: F1={metadata.get('f1_score')}, "
            f"AUC={metadata.get('auc_roc')}, "
            f"version={metadata.get('version')}"
        )


if __name__ == "__main__":
    main()
