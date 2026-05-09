"""Bucle del consumidor Kafka para el servicio Anonymizer.

Aplica seudonimización HMAC al ``device_uuid`` y ruido de Laplace a
los valores continuos antes de escribir a InfluxDB.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Callable

from anonymizer.differential_privacy import apply_laplace_noise
from anonymizer.influx_writer import to_line_protocol
from anonymizer.models import AnonymizedBatch, AnonymizedReading
from anonymizer.pseudonymizer import pseudonymize_device_uuid

logger = logging.getLogger(__name__)

TOPIC_IN = os.environ.get("KAFKA_TOPIC_IN", "cvs.telemetry.normalized")


def build_consumer() -> Any:
    from confluent_kafka import Consumer
    return Consumer({
        "bootstrap.servers": os.environ.get(
            "KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"
        ),
        "security.protocol": os.environ.get(
            "KAFKA_SECURITY_PROTOCOL", "PLAINTEXT"
        ),
        "group.id": os.environ.get("KAFKA_CONSUMER_GROUP", "anonymizer-cg"),
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
    })


def deserialize_batch(raw_bytes: bytes) -> AnonymizedBatch:
    payload = json.loads(raw_bytes.decode("utf-8"))
    return AnonymizedBatch.model_validate(payload)


def anonymize(batch: AnonymizedBatch) -> AnonymizedBatch:
    """Reemplaza el ``device_uuid`` por su HMAC y aplica ruido Laplace
    al valor de cada lectura."""
    new_uuid = pseudonymize_device_uuid(batch.device_uuid)
    new_readings = [
        AnonymizedReading(
            sensor_type=r.sensor_type,
            value=apply_laplace_noise(r.value, r.sensor_type),
            unit=r.unit,
            sampled_at=r.sampled_at,
        )
        for r in batch.readings
    ]
    return AnonymizedBatch(
        device_uuid=new_uuid,
        batch_timestamp=batch.batch_timestamp,
        readings=new_readings,
        app_version=batch.app_version,
        consent_hash=batch.consent_hash,
    )


def _is_partition_eof(err) -> bool:
    try:
        from confluent_kafka import KafkaError
        return err.code() == KafkaError._PARTITION_EOF  # noqa: SLF001
    except ImportError:
        return False


def run_consumer_loop(
    consumer: Any,
    write_lines: Callable[[list[str]], None] | None = None,
) -> None:
    """Bucle principal: deserializa, anonimiza y escribe el ``line
    protocol`` resultante. ``write_lines`` se inyecta para facilitar
    pruebas; por defecto solo loguea (la conexión real a InfluxDB la
    activa el sidecar)."""
    if write_lines is None:
        def _default_write(lines: list[str]) -> None:
            for line in lines:
                logger.debug("influx-line: %s", line)
        write_lines = _default_write

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

            anon = anonymize(batch)
            write_lines(to_line_protocol(anon))
            consumer.commit(message=msg, asynchronous=False)
    finally:
        consumer.close()
