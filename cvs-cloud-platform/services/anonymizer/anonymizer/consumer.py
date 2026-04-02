"""Kafka consumer for normalized telemetry."""
from __future__ import annotations
import json
import os
from confluent_kafka import Consumer
from anonymizer.models import AnonymizedBatch

TOPIC_IN = "cvs.telemetry.normalized"


def build_consumer() -> Consumer:
    return Consumer(
        {
            "bootstrap.servers": os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
            "group.id": "anonymizer-cg",
            "auto.offset.reset": "earliest",
        }
    )


def deserialize_batch(raw_bytes: bytes) -> AnonymizedBatch:
    payload = json.loads(raw_bytes.decode("utf-8"))
    return AnonymizedBatch.model_validate(payload)
