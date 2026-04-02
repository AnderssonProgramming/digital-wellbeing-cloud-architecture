"""HMAC-SHA256 pseudonymization of device identifiers."""
from __future__ import annotations
import hashlib
import hmac
import os


def pseudonymize_device_uuid(device_uuid: str, org_secret: str | None = None) -> str:
    """
    Replace a real device UUID with a deterministic pseudonym.

    Uses HMAC-SHA256(org_secret, device_uuid) truncated to 32 hex characters.
    The org_secret is loaded from the ORG_ANONYMIZATION_SECRET environment variable.

    Args:
        device_uuid: The original device UUID from the mobile agent.
        org_secret: Optional override for testing. Defaults to env var.

    Returns:
        32-character hexadecimal pseudonymous identifier.
    """
    secret = org_secret or os.environ.get("ORG_ANONYMIZATION_SECRET", "default-secret")
    digest = hmac.new(
        key=secret.encode("utf-8"),
        msg=device_uuid.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()
    return digest[:32]
