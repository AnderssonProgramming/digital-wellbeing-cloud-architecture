"""Pipeline de ingeniería de ``features`` para el modelo CVS.

Construye los nueve ``features`` por usuario-día a partir de lecturas
horarias de InfluxDB. La función ``query_feature_window`` ejecuta la
consulta Flux y ``build_features`` agrega por usuario-día.
"""
from __future__ import annotations

import pandas as pd

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

MAX_NULL_FRACTION: float = 0.20  # Se descarta el usuario-día si supera esto.
ESTIMATED_SCREEN_BRIGHTNESS_LUX: float = 200.0
EVENING_HOUR_THRESHOLD: int = 20
SESSION_BLOCK_MIN: int = 20


def _safe_float(series: pd.Series, op: str, default: float = 0.0) -> float:
    """Devuelve el agregado pedido o ``default`` si la serie es vacía."""
    if series.empty:
        return default
    if op == "std" and len(series) < 2:
        return 0.0
    fn = {
        "mean": series.mean,
        "std": lambda: series.std(ddof=0),
        "max": series.max,
        "min": series.min,
        "sum": series.sum,
    }[op]
    return float(fn())


def _row_for_group(uuid: str, day, g: pd.DataFrame) -> dict:
    """Calcula los nueve ``features`` para un (usuario, día)."""
    lux = g["AMBIENT_LIGHT"].dropna()
    prox = g["PROXIMITY"].dropna()
    screen = g["SCREEN_TIME"].dropna()

    total_screen = _safe_float(screen, "sum")
    mean_lux = _safe_float(lux, "mean")

    evening = g[g["hour"] >= EVENING_HOUR_THRESHOLD]["SCREEN_TIME"].dropna()
    evening_total = _safe_float(evening, "sum")
    evening_screen_ratio = (
        evening_total / total_screen if total_screen > 0 else 0.0
    )

    breaks = int((screen <= 0.0).sum()) if not screen.empty else 0
    blocks = max(1, len(screen))

    return {
        "device_uuid": uuid,
        "day": day,
        "mean_lux_daily": mean_lux,
        "std_lux_daily": _safe_float(lux, "std"),
        "mean_proximity_cm": _safe_float(prox, "mean"),
        "min_proximity_cm": _safe_float(prox, "min"),
        "total_screen_min": total_screen,
        "max_cont_session_min": _safe_float(screen, "max"),
        "lux_screen_ratio": mean_lux / ESTIMATED_SCREEN_BRIGHTNESS_LUX,
        "evening_screen_ratio": evening_screen_ratio,
        "break_compliance_score": breaks / blocks,
    }


def _per_user_day(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega un DataFrame ``hora x usuario`` a una fila por usuario-día."""
    df = df.copy()
    df["_time"] = pd.to_datetime(df["_time"], utc=True)
    df["day"] = df["_time"].dt.date
    df["hour"] = df["_time"].dt.hour

    rows = [
        _row_for_group(uuid, day, g)
        for (uuid, day), g in df.groupby(["device_uuid", "day"], sort=False)
    ]
    out = pd.DataFrame(rows)
    if out.empty:
        return out

    null_frac = out[FEATURE_NAMES].isna().mean(axis=1)
    return out[null_frac <= MAX_NULL_FRACTION].reset_index(drop=True)


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula el vector de 9 ``features`` por usuario-día a partir de
    un DataFrame con columnas ``device_uuid``, ``_time``, ``AMBIENT_LIGHT``,
    ``PROXIMITY`` y ``SCREEN_TIME`` (pivoteado desde ``sensor_type``).

    Devuelve un DataFrame con las columnas de :data:`FEATURE_NAMES` más
    ``device_uuid`` y ``day``.
    """
    if df.empty:
        return pd.DataFrame(columns=["device_uuid", "day", *FEATURE_NAMES])

    required = {"device_uuid", "_time"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Columnas faltantes en el DataFrame: {missing}")

    # Si las columnas pivoteadas no existen, las creamos vacías.
    for col in ("AMBIENT_LIGHT", "PROXIMITY", "SCREEN_TIME"):
        if col not in df.columns:
            df[col] = pd.NA

    return _per_user_day(df)


def query_feature_window(influx_client, uuid: str, days: int = 30) -> pd.DataFrame:
    """Ejecuta la consulta Flux contra InfluxDB y devuelve un DataFrame
    pivotado listo para :func:`build_features`.

    Args:
        influx_client: cliente ``InfluxDBClient`` configurado.
        uuid: identificador seudónimo del dispositivo.
        days: ventana de retroceso en días (por defecto 30).
    """
    flux = f"""
from(bucket: "cvs_platform")
  |> range(start: -{days}d)
  |> filter(fn: (r) => r["_measurement"] == "sensor_readings")
  |> filter(fn: (r) => r["device_uuid"] == "{uuid}")
  |> aggregateWindow(every: 1h, fn: mean, createEmpty: false)
  |> pivot(rowKey: ["_time"],
           columnKey: ["sensor_type"],
           valueColumn: "_value")
"""

    query_api = influx_client.query_api()
    df = query_api.query_data_frame(flux)
    if isinstance(df, list):
        df = pd.concat(df, ignore_index=True) if df else pd.DataFrame()
    if df.empty:
        return pd.DataFrame(
            columns=[
                "device_uuid",
                "_time",
                "AMBIENT_LIGHT",
                "PROXIMITY",
                "SCREEN_TIME",
            ]
        )
    return df
