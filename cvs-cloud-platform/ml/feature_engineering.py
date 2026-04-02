"""
Feature engineering pipeline.
Builds the 9-feature matrix from raw InfluxDB sensor readings (Table 7, paper).
"""
from __future__ import annotations
import pandas as pd

FEATURE_NAMES = [
    "mean_lux_daily", "std_lux_daily", "mean_proximity_cm", "min_proximity_cm",
    "total_screen_min", "max_cont_session_min", "lux_screen_ratio",
    "evening_screen_ratio", "break_compliance_score",
]

MAX_NULL_FRACTION: float = 0.20   # Discard user-day if > 20% of features are null


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute the 9-feature vector per user-day from pivoted InfluxDB data.

    Input df columns expected: device_uuid, _time (hourly), AMBIENT_LIGHT,
    PROXIMITY, SCREEN_TIME (pivoted from sensor_type).

    Returns DataFrame with columns = FEATURE_NAMES + device_uuid.
    """
    # TODO: implement aggregation per device_uuid per day
    raise NotImplementedError


def query_feature_window(influx_client, uuid: str, days: int = 30) -> pd.DataFrame:
    """
    Execute the Flux query from Listing 2 (paper) against InfluxDB and return
    a pivoted DataFrame ready for build_features().

    Args:
        influx_client: InfluxDB Python client instance.
        uuid: Pseudonymous device UUID.
        days: Lookback window in days (default 30).

    Returns:
        DataFrame with hourly averaged sensor readings, or empty DataFrame if
        no data found.
    """
    flux = f"""
    from(bucket: "cvs_platform")
      |> range(start: -{days}d)
      |> filter(fn: (r) => r["_measurement"] == "sensor_readings")
      |> filter(fn: (r) => r["device_uuid"] == "{uuid}")
      |> aggregateWindow(every: 1h, fn: mean, createEmpty: false)
      |> pivot(rowKey: ["_time"], columnKey: ["sensor_type"], valueColumn: "_value")
    """
    # TODO: execute query via influx_client.query_api().query_data_frame(flux)
    raise NotImplementedError
