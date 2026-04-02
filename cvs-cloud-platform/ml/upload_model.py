"""Upload trained model artifacts to S3."""
from __future__ import annotations
import json
import os
from pathlib import Path
import boto3

RESULTS_DIR = Path(__file__).parent / "results"
MODEL_PATH = RESULTS_DIR / "model.joblib"
METADATA_PATH = RESULTS_DIR / "model_metadata.json"


def main() -> None:
    bucket = os.environ.get("S3_MODEL_BUCKET", "cvs-model-artifacts")
    s3 = boto3.client("s3")

    metadata = json.loads(METADATA_PATH.read_text())
    version = str(metadata.get("version", "unknown"))

    model_key = f"models/{version}/model.joblib"
    metadata_key = f"models/{version}/model_metadata.json"

    s3.upload_file(str(MODEL_PATH), bucket, model_key)
    s3.upload_file(str(METADATA_PATH), bucket, metadata_key)

    s3.put_object(
        Bucket=bucket,
        Key="models/latest.json",
        Body=json.dumps({"version": version, "model_key": model_key}).encode("utf-8"),
        ContentType="application/json",
    )

    print(f"Uploaded model to s3://{bucket}/{model_key}")
    print(f"Uploaded metadata to s3://{bucket}/{metadata_key}")


if __name__ == "__main__":
    main()
