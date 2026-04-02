"""Kafka consumer loop for the Rule Engine."""
from __future__ import annotations
import logging
import os
from confluent_kafka import Consumer, KafkaError
from rule_engine.models import TelemetryBatch

logger = logging.getLogger(__name__)

KAFKA_BOOTSTRAP_SERVERS = os.environ["KAFKA_BOOTSTRAP_SERVERS"]
KAFKA_CONSUMER_GROUP = "rule-engine-cg"
TOPIC_RAW = "cvs.telemetry.raw"


def build_consumer() -> Consumer:
    return Consumer({
        "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
        "group.id": KAFKA_CONSUMER_GROUP,
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
        "security.protocol": "SSL",
    })


def deserialize_batch(raw_bytes: bytes) -> TelemetryBatch:
    """Deserialize Avro bytes into a TelemetryBatch Pydantic model."""
    # TODO: implement Avro deserialization using fastavro + Schema Registry
    raise NotImplementedError


def run_consumer_loop(consumer: Consumer) -> None:
    """Main consumer loop. Commit offsets only after successful downstream publish."""
    consumer.subscribe([TOPIC_RAW])
    try:
        while True:
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                logger.error("Consumer error: %s", msg.error())
                continue
            batch = deserialize_batch(msg.value())
            # TODO: call rule evaluation functions and publish alerts
            consumer.commit(message=msg, asynchronous=False)
    finally:
        consumer.close()
