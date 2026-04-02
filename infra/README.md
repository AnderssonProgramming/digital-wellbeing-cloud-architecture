# Infrastructure — Terraform Modules

## Prerequisites
- AWS CLI configured with `AdministratorAccess` (for initial setup only)
- Terraform >= 1.6

## Modules

| Module | Description |
|---|---|
| `eks/` | EKS 1.29 cluster with 3 node groups: ingestion (t3.medium x2), processing (t3.medium x3), data-ml (t3.large x2) |
| `msk/` | AWS MSK Kafka 3.6 cluster with 3 brokers (kafka.t3.small, 50 GB gp3 each) |
| `s3/` | S3 bucket for model artifacts with versioning and 180-day lifecycle policy |

## Usage

```bash
terraform init
terraform plan -var-file=environments/staging.tfvars
terraform apply -var-file=environments/staging.tfvars
```

## Required Variables

| Variable | Description |
|---|---|
| `aws_region` | AWS region (default: us-east-1) |
| `cluster_name` | EKS cluster name |
| `kafka_broker_count` | Number of MSK brokers (default: 3) |
| `s3_model_bucket_name` | Name for the model artifact S3 bucket |
