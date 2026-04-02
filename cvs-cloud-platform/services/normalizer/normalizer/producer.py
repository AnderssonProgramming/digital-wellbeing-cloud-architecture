"""Kafka producer for normalized telemetry."""
from __future__ import annotations
import json
import os
from confluent_kafka import Producer
from normalizer.models import NormalizedBatch

TOPIC_OUT = "cvs.telemetry.normalized"


def build_producer() -> Producer:
    return Producer({"bootstrap.servers": os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")})


def publish_batch(producer: Producer, batch: NormalizedBatch) -> None:
    producer.produce(TOPIC_OUT, json.dumps(batch.model_dump()).encode("utf-8"))
    producer.flush(5)
