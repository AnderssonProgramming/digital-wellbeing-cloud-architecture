"""InfluxDB query helpers for feature retrieval."""
from __future__ import annotations
from influxdb_client import InfluxDBClient


def make_client(url: str, token: str, org: str) -> InfluxDBClient:
    return InfluxDBClient(url=url, token=token, org=org)
