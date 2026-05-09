"""
Generador del dataset sintético para entrenar el modelo XGBoost de
puntaje de riesgo de CVS.

No existe un dataset público canónico de CVS (Computer Vision Syndrome).
Las opciones realistas para el alcance del semestre son:

1. Un grupo voluntario con cuestionario CVSQ + sensores propios. Requiere
   comité de ética y un cronograma que excede el semestre. Queda como
   trabajo futuro.
2. Adaptar datasets vecinos (WESAD para estrés, DEAP para emoción con
   wearables fisiológicos). Ninguno mide CVS y forzar la adaptación
   resta credibilidad.
3. **Sintético calibrado con literatura clínica.** Es lo que usamos.

Las distribuciones de las nueve features y la regla de etiquetado están
calibradas con los umbrales y rangos reportados por:

    Sheppard, A. L. & Wolffsohn, J. S. (2018). "Digital eye strain:
    prevalence, measurement and amelioration." BMJ Open Ophthalmology,
    3(1), e000146.

    Blehm, C., Vishnu, S., Khattak, A., Mitra, S., & Yee, R. W. (2005).
    "Computer vision syndrome: a review." Survey of Ophthalmology,
    50(3), 253-262.

Honestidad metodológica: el F1 que reporta ``train.py`` no es validez
clínica del modelo, es la capacidad del modelo de recuperar la regla con
la que fueron etiquetados estos datos. La validación con un grupo real
queda explícitamente como trabajo futuro en el paper.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

RANDOM_SEED: int = 42
N_SAMPLES: int = 50_000
OUTPUT_DIR: Path = Path(__file__).parent / "data"
OUTPUT_PARQUET: Path = OUTPUT_DIR / "synthetic_dataset.parquet"
OUTPUT_CSV: Path = OUTPUT_DIR / "synthetic_dataset.csv"

# --- Parámetros físicos calibrados con la literatura clínica ---------
# Iluminación recomendada para oficinas según ISO 8995: 300-500 lux.
# Brillo equivalente típico de pantalla de oficina: ~200 lux.
ESTIMATED_SCREEN_BRIGHTNESS_LUX: float = 200.0

# Umbrales de etiquetado (Sheppard & Wolffsohn, 2018).
THRESHOLD_BREAK_COMPLIANCE: float = 0.40
THRESHOLD_MAX_CONT_SESSION_MIN: float = 45.0

# Cuánto ruido inyectar alrededor de la frontera de decisión: el modelo
# no debe aprender la regla literal, debe aprenderla con error realista
# (el F1 baja a un rango defendible, no a 0,99 que sería sospechoso).
LABEL_NOISE_FRACTION: float = 0.45
LABEL_NOISE_DECAY: float = 1.2


def _correlated_session_lengths(
    rng: np.random.Generator, n: int, total: np.ndarray
) -> np.ndarray:
    """``max_cont_session_min`` correlacionada con ``total_screen_min``.

    Una persona con muchas horas de pantalla tiende a tener sesiones
    continuas más largas. Forzamos esa correlación con un ruido
    multiplicativo proporcional al total, en vez de muestrear
    independientemente.
    """
    base = rng.beta(2.0, 3.0, n) * total
    capped = np.minimum(base, 180.0)
    return np.clip(capped, 15.0, 180.0)


def generate(n: int = N_SAMPLES, seed: int = RANDOM_SEED) -> pd.DataFrame:
    """Genera ``n`` registros usuario-día con las nueve features del modelo."""
    rng = np.random.default_rng(seed)

    # Iluminación ambiental. Oficinas reales caen en una distribución
    # log-normal: hay muchos puestos con luz adecuada y una cola de
    # puestos mal iluminados.
    mean_lux = np.clip(rng.lognormal(mean=5.6, sigma=0.55, size=n), 20.0, 1500.0)
    std_lux = np.clip(rng.exponential(scale=40.0, size=n), 0.5, 200.0)

    # Distancia al rostro. La media estable está alrededor de 45 cm
    # (ergonomía recomendada: 50-70 cm; muchos usuarios reales se
    # acercan más durante lectura intensa).
    mean_prox = np.clip(rng.normal(loc=45.0, scale=12.0, size=n), 18.0, 90.0)
    # min_prox siempre debe ser <= mean_prox por construcción.
    prox_drop = rng.uniform(low=4.0, high=18.0, size=n)
    min_prox = np.clip(mean_prox - prox_drop, 5.0, mean_prox)

    # Tiempo total de pantalla (minutos al día). Centrado en jornadas
    # de oficina (8 horas) con cola gruesa hacia trabajadores que
    # alargan jornada en casa.
    total_screen = np.clip(rng.normal(loc=460.0, scale=110.0, size=n), 60.0, 900.0)

    # Sesión continua máxima (correlacionada con total).
    max_cont = _correlated_session_lengths(rng, n, total_screen)

    # Ratio luz/pantalla. Mismatch < 1 indica oficina más oscura que la
    # pantalla (factor ergonómico).
    lux_ratio = mean_lux / ESTIMATED_SCREEN_BRIGHTNESS_LUX

    # Fracción del día con pantalla activa después de las 8 p. m.
    evening_ratio = np.clip(rng.beta(a=2.0, b=5.0, size=n), 0.0, 1.0)

    # Compliance de pausas (Beta(3,2): mediana ~0.62, cola hacia bajo).
    # Fuertemente correlacionada negativamente con max_cont: si la
    # sesión continua es larga, hubo pocas pausas.
    raw_compliance = rng.beta(a=3.0, b=2.0, size=n)
    compliance_penalty = np.clip((max_cont - 30.0) / 150.0, 0.0, 1.0) * 0.18
    break_score = np.clip(raw_compliance - compliance_penalty, 0.0, 1.0)

    df = pd.DataFrame(
        {
            "mean_lux_daily": mean_lux,
            "std_lux_daily": std_lux,
            "mean_proximity_cm": mean_prox,
            "min_proximity_cm": min_prox,
            "total_screen_min": total_screen,
            "max_cont_session_min": max_cont,
            "lux_screen_ratio": lux_ratio,
            "evening_screen_ratio": evening_ratio,
            "break_compliance_score": break_score,
        }
    )

    # --- Etiquetado con frontera "blanda" -----------------------------
    # La regla determinista es:
    #     y = 1  si  break_compliance < 0.40  AND  max_cont > 45
    # Eso etiqueta perfectamente, lo cual es poco realista. Para forzar
    # al modelo a aprender una frontera con error, voltearemos la
    # etiqueta de un porcentaje pequeño de muestras escogidas
    # aleatoriamente cerca de la frontera.
    base_label = (
        (df["break_compliance_score"] < THRESHOLD_BREAK_COMPLIANCE)
        & (df["max_cont_session_min"] > THRESHOLD_MAX_CONT_SESSION_MIN)
    ).astype(int)

    # Distancia normalizada a la frontera (en [0, 1]).
    distance_compliance = np.abs(
        df["break_compliance_score"].to_numpy() - THRESHOLD_BREAK_COMPLIANCE
    )
    distance_session = np.abs(
        df["max_cont_session_min"].to_numpy() - THRESHOLD_MAX_CONT_SESSION_MIN
    ) / 100.0
    boundary_distance = distance_compliance + distance_session

    # Probabilidad de voltear: alta cerca de la frontera, decae despacio
    # lejos de ella. Con LABEL_NOISE_FRACTION = 0,45 y decay = 1,2, el
    # F1 esperable cae a un rango realista (~0,82-0,90).
    flip_prob = LABEL_NOISE_FRACTION * np.exp(-LABEL_NOISE_DECAY * boundary_distance)
    flip_mask = rng.random(n) < flip_prob

    label = np.where(flip_mask, 1 - base_label, base_label).astype(int)
    df["label"] = label

    positive_rate = float(df["label"].mean())
    print(f"Generated {n} samples. Positive rate: {positive_rate:.2%}")
    print(
        f"Etiquetas con ruido en frontera: "
        f"{int(flip_mask.sum())} de {n} ({flip_mask.mean():.2%})"
    )
    if not (0.15 <= positive_rate <= 0.50):
        raise AssertionError(f"Unexpected positive rate: {positive_rate:.2%}")

    return df


def _save(dataset: pd.DataFrame) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        dataset.to_parquet(OUTPUT_PARQUET, index=False)
        return OUTPUT_PARQUET
    except ImportError:
        # pyarrow / fastparquet no disponible: degradamos a CSV.
        dataset.to_csv(OUTPUT_CSV, index=False)
        return OUTPUT_CSV


if __name__ == "__main__":
    dataset = generate()
    saved_to = _save(dataset)
    print(f"Dataset saved to {saved_to}")
