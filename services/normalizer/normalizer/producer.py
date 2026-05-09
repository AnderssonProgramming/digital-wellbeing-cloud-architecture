"""Kafka producer for normalized telemetry."""
from __future__ import annotations
import json
import os
from typing import Any

from normalizer.models import NormalizedBatch

TOPIC_OUT = "cvs.telemetry.normalized"


def build_producer() -> Any:
    from confluent_kafka import Producer
    return Producer({"bootstrap.servers": os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")})


def publish_batch(producer: Any, batch: NormalizedBatch) -> None:
    producer.produce(TOPIC_OUT, json.dumps(batch.model_dump()).encode("utf-8"))
    producer.flush(5)
