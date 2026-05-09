"""Bucle del consumidor Kafka para el Rule Engine.

Para el prototipo deserializamos los lotes como JSON (es lo que el
agente Android publica vía MQTT y lo que el bridge a Kafka reenvía).
La opción Avro queda referenciada para evolución futura.
"""
from __future__ import annotations
import json
import logging
import os
from typing import Any

from rule_engine import rules
from rule_engine.models import TelemetryBatch
from rule_engine.producer import publish_alert

logger = logging.getLogger(__name__)

KAFKA_BOOTSTRAP_SERVERS = os.environ.get(
    "KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"
)
KAFKA_SECURITY_PROTOCOL = os.environ.get("KAFKA_SECURITY_PROTOCOL", "PLAINTEXT")
KAFKA_CONSUMER_GROUP = os.environ.get(
    "KAFKA_CONSUMER_GROUP", "rule-engine-cg"
)
TOPIC_RAW = os.environ.get("KAFKA_TOPIC_IN", "cvs.telemetry.raw")


def build_consumer() -> Any:
    from confluent_kafka import Consumer
    return Consumer({
        "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
        "security.protocol": KAFKA_SECURITY_PROTOCOL,
        "group.id": KAFKA_CONSUMER_GROUP,
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
    })


def deserialize_batch(raw_bytes: bytes) -> TelemetryBatch:
    """Deserializa los bytes Kafka como JSON UTF-8 a un TelemetryBatch."""
    payload = json.loads(raw_bytes.decode("utf-8"))
    return TelemetryBatch.model_validate(payload)


def evaluate_all_rules(
    batch: TelemetryBatch,
    proximity_state: dict[str, list[float]],
) -> list:
    """Aplica las tres reglas y devuelve una lista de alertas (puede
    estar vacía)."""
    alerts = []
    for rule_fn, args in (
        (rules.evaluate_20_20_20, (batch,)),
        (rules.evaluate_proximity_violation, (batch, proximity_state)),
        (rules.evaluate_lux_mismatch, (batch,)),
    ):
        alert = rule_fn(*args)
        if alert is not None:
            alerts.append(alert)
    return alerts


def _is_partition_eof(err) -> bool:
    """Compara contra ``KafkaError._PARTITION_EOF`` con import diferido,
    de modo que el módulo se pueda importar sin la librería instalada."""
    try:
        from confluent_kafka import KafkaError
        return err.code() == KafkaError._PARTITION_EOF  # noqa: SLF001
    except ImportError:
        return False


def run_consumer_loop(consumer: Any, producer: Any | None = None) -> None:
    """Bucle principal. Por cada mensaje deserializa, evalúa las reglas
    y publica las alertas resultantes; solo hace commit del offset
    después de publicar."""
    proximity_state: dict[str, list[float]] = {}

    consumer.subscribe([TOPIC_RAW])
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
                from rule_engine.producer import build_producer
                producer = build_producer()
            alerts = evaluate_all_rules(batch, proximity_state)
            for alert in alerts:
                publish_alert(producer, alert)

            consumer.commit(message=msg, asynchronous=False)
    finally:
        consumer.close()
