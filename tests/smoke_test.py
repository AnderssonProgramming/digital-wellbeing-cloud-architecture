"""
End-to-end smoke test for the CVS Platform staging deployment.

Validates:
  1. POST /v1/telemetry/ingest returns 202.
  2. After 30s, GET /v1/scores/{uuid}/current returns 200 with valid risk_score.
  3. GET /v1/health on all microservices returns 200.

Usage:
  BASE_URL=https://staging.cvs-platform.internal JWT_TOKEN=<token> python tests/smoke_test.py
"""
from __future__ import annotations
import os
import sys
import time
import uuid
import json
import logging
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = os.environ.get("BASE_URL", "http://localhost:8004")
JWT_TOKEN = os.environ.get("JWT_TOKEN", "")
HEADERS = {"Authorization": f"Bearer {JWT_TOKEN}", "Content-Type": "application/json"}
TEST_UUID = str(uuid.uuid4())


def test_health_endpoints() -> bool:
    services = {
        "rule-engine":   os.environ.get("RULE_ENGINE_URL", "http://localhost:8001"),
        "normalizer":    os.environ.get("NORMALIZER_URL",  "http://localhost:8002"),
        "anonymizer":    os.environ.get("ANONYMIZER_URL",  "http://localhost:8003"),
        "inference-svc": BASE_URL,
    }
    all_ok = True
    for name, url in services.items():
        try:
            r = requests.get(f"{url}/v1/health", timeout=5)
            ok = r.status_code == 200
            logger.info("[%s] %s health: %s", "PASS" if ok else "FAIL", name, r.status_code)
            all_ok = all_ok and ok
        except Exception as e:
            logger.error("[FAIL] %s health check failed: %s", name, e)
            all_ok = False
    return all_ok


def test_ingestion_and_scoring() -> bool:
    payload = {
        "device_uuid": TEST_UUID,
        "batch_timestamp": int(time.time() * 1000),
        "readings": [
            {"sensor_type": "AMBIENT_LIGHT", "value": 250.0,
             "unit": "lux", "sampled_at": int(time.time() * 1000)},
            {"sensor_type": "PROXIMITY", "value": 35.0,
             "unit": "cm",  "sampled_at": int(time.time() * 1000)},
            {"sensor_type": "SCREEN_TIME", "value": 50.0,
             "unit": "min", "sampled_at": int(time.time() * 1000)},
        ],
        "app_version": "1.0.0",
        "consent_hash": "abc123def456abc123def456abc12345",
    }
    r = requests.post(f"{BASE_URL}/v1/telemetry/ingest", json=payload, headers=HEADERS, timeout=10)
    if r.status_code not in (200, 202):
        logger.error("[FAIL] Ingest returned %s: %s", r.status_code, r.text)
        return False
    logger.info("[PASS] Ingest: 202 Accepted")

    logger.info("Waiting 30s for pipeline processing...")
    time.sleep(30)

    r2 = requests.get(f"{BASE_URL}/v1/scores/{TEST_UUID}/current", headers=HEADERS, timeout=10)
    if r2.status_code != 200:
        logger.error("[FAIL] Score endpoint returned %s", r2.status_code)
        return False
    body = r2.json()
    score = body.get("risk_score", -1)
    if not (0.0 <= score <= 1.0):
        logger.error("[FAIL] Invalid risk_score: %s", score)
        return False
    logger.info("[PASS] Risk score: %.4f (level: %s)", score, body.get("risk_level"))
    return True


if __name__ == "__main__":
    ok = test_health_endpoints() and test_ingestion_and_scoring()
    sys.exit(0 if ok else 1)
