"""S3 helpers for model artifact download."""
from __future__ import annotations
from pathlib import Path
import boto3


def download_model(bucket: str, key: str, target_path: Path) -> Path:
    s3 = boto3.client("s3")
    target_path.parent.mkdir(parents=True, exist_ok=True)
    s3.download_file(bucket, key, str(target_path))
    return target_path
