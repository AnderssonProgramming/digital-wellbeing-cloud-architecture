"""Write anonymized records to InfluxDB line protocol (adapter stub)."""
from __future__ import annotations
from anonymizer.models import AnonymizedBatch


def to_line_protocol(batch: AnonymizedBatch) -> list[str]:
    lines: list[str] = []
    for reading in batch.readings:
        line = (
            f"sensor_readings,device_uuid={batch.device_uuid},sensor_type={reading.sensor_type} "
            f"value={reading.value} {reading.sampled_at * 1000000}"
        )
        lines.append(line)
    return lines
