"""Kafka consumer for raw telemetry."""
from __future__ import annotations
import json
import os
from confluent_kafka import Consumer
from normalizer.models import NormalizedBatch

TOPIC_IN = "cvs.telemetry.raw"


def build_consumer() -> Consumer:
    return Consumer(
        {
            "bootstrap.servers": os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
            "group.id": "normalizer-cg",
            "auto.offset.reset": "earliest",
        }
    )


def deserialize_batch(raw_bytes: bytes) -> NormalizedBatch:
    payload = json.loads(raw_bytes.decode("utf-8"))
    return NormalizedBatch.model_validate(payload)
