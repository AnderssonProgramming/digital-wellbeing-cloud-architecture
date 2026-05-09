"""Bucle del consumidor Kafka para el servicio Normalizer."""
from __future__ import annotations

import json
import logging
import os
from typing import Any

from normalizer.models import NormalizedBatch
from normalizer.normalizer import normalize_batch
from normalizer.producer import build_producer, publish_batch

logger = logging.getLogger(__name__)

TOPIC_IN = os.environ.get("KAFKA_TOPIC_IN", "cvs.telemetry.raw")


def build_consumer() -> Any:
    from confluent_kafka import Consumer
    return Consumer({
        "bootstrap.servers": os.environ.get(
            "KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"
        ),
        "security.protocol": os.environ.get(
            "KAFKA_SECURITY_PROTOCOL", "PLAINTEXT"
        ),
        "group.id": os.environ.get(
            "KAFKA_CONSUMER_GROUP", "normalizer-cg"
        ),
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
    })


def deserialize_batch(raw_bytes: bytes) -> NormalizedBatch:
    payload = json.loads(raw_bytes.decode("utf-8"))
    return NormalizedBatch.model_validate(payload)


def _is_partition_eof(err) -> bool:
    try:
        from confluent_kafka import KafkaError
        return err.code() == KafkaError._PARTITION_EOF  # noqa: SLF001
    except ImportError:
        return False


def run_consumer_loop(
    consumer: Any, producer: Any | None = None
) -> None:
    """Bucle principal: deserializa, normaliza y reenvía al
    siguiente tópico. Solo hace commit del offset después de
    haber reenviado correctamente."""
    consumer.subscribe([TOPIC_IN])
    try:
        while True:
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                continue
            if msg.error():
                if _is_partition_eof(msg.error()):
                    continue
                logger.error("Error de consumidor: %s", msg.error())
                continue
            try:
                batch = deserialize_batch(msg.value())
            except ValueError as exc:
                logger.warning("Lote inválido descartado: %s", exc)
                consumer.commit(message=msg, asynchronous=False)
                continue

            if producer is None:
                producer = build_producer()
            normalized = normalize_batch(batch)
            publish_batch(producer, normalized)
            consumer.commit(message=msg, asynchronous=False)
    finally:
        consumer.close()
