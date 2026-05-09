"""Kafka producer utilities for Rule Engine alerts."""
from __future__ import annotations
import json
import logging
import os
from typing import Any

from rule_engine.models import Alert

logger = logging.getLogger(__name__)
TOPIC_ALERTS = "cvs.alerts.immediate"


def build_producer() -> Any:
    from confluent_kafka import Producer
    return Producer(
        {
            "bootstrap.servers": os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
            "security.protocol": os.environ.get("KAFKA_SECURITY_PROTOCOL", "PLAINTEXT"),
        }
    )


def publish_alert(producer: Any, alert: Alert) -> None:
    payload = json.dumps(alert.model_dump()).encode("utf-8")
    producer.produce(TOPIC_ALERTS, payload)
    producer.flush(5)
    logger.info("Published alert for device=%s rule=%s", alert.device_uuid, alert.rule_id)
