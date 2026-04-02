# CVS Cloud Platform

Distributed cloud-native platform for predictive detection and mitigation of
Computer Vision Syndrome (CVS) through behavioral analytics.

## Architecture Overview

Four-layer architecture:
- **Layer 1 — Edge Ingestion**: Android mobile agent (Kotlin + WorkManager + MQTT v5)
- **Layer 2 — Cloud Gateway & Messaging**: Kong Gateway 3.x + Apache Kafka 3.6 + Confluent Schema Registry
- **Layer 3 — Async Processing & Persistence**: Rule Engine + Normalizer + Anonymizer (Python 3.11 + FastAPI) + InfluxDB 2.7
- **Layer 4 — ML Inference & Dashboard**: XGBoost CVS Risk Scorer + Grafana Dashboards + Alert Dispatcher

## Repository Structure

| Directory | Description |
|---|---|
| `infra/` | Terraform modules for EKS, MSK, S3 |
| `k8s/` | Kubernetes manifests: namespaces, RBAC, Istio, NetworkPolicies |
| `helm/` | Helm 3 charts for each microservice |
| `services/` | Python 3.11 FastAPI microservices |
| `ml/` | XGBoost training pipeline and drift monitoring |
| `mobile/` | Android Kotlin agent |
| `schemas/` | Apache Avro schemas |
| `tests/` | Integration, smoke, load, and privacy audit tests |
| `grafana/` | Grafana dashboard JSON definitions |
| `paper/` | LaTeX article deliverables |

## Microservices

| Service | Port | Kafka In | Kafka Out |
|---|---|---|---|
| rule-engine | 8001 | `cvs.telemetry.raw` | `cvs.alerts.immediate` |
| normalizer | 8002 | `cvs.telemetry.raw` | `cvs.telemetry.normalized` |
| anonymizer | 8003 | `cvs.telemetry.normalized` | — (writes InfluxDB) |
| inference-svc | 8004 | — | `cvs.inference.scores` |

## Kafka Topics

| Topic | Partitions | Replicas | Retention |
|---|---|---|---|
| `cvs.telemetry.raw` | 12 | 3 | 7d |
| `cvs.telemetry.normalized` | 12 | 3 | 7d |
| `cvs.alerts.immediate` | 6 | 3 | 24h |
| `cvs.inference.scores` | 6 | 3 | 30d |

## Target SLOs

| Attribute | SLO |
|---|---|
| Availability | ≥ 99.5% uptime/month |
| Ingestion latency | P99 ≤ 500ms under 10k concurrent producers |
| Privacy | Zero raw PII in InfluxDB |
| ML Accuracy | F1 ≥ 0.75, AUC-ROC ≥ 0.80 |
| Inference latency | P99 ≤ 100ms |

## Prerequisites

- AWS CLI configured with appropriate IAM permissions
- Terraform >= 1.6
- kubectl >= 1.29
- Helm >= 3.13
- Python >= 3.11
- Docker >= 24
- Android Studio Hedgehog (2023.1.1) or later

## Quick Start

```bash
# 1. Provision infrastructure
cd infra/terraform && terraform init && terraform apply

# 2. Apply Kubernetes manifests
kubectl apply -f k8s/namespaces.yaml
kubectl apply -f k8s/rbac.yaml
kubectl apply -f k8s/network-policies.yaml
kubectl apply -f k8s/istio/

# 3. Deploy services to staging
helm upgrade --install rule-engine helm/rule-engine/ -n ns-staging
helm upgrade --install normalizer helm/normalizer/ -n ns-staging
helm upgrade --install anonymizer helm/anonymizer/ -n ns-staging
helm upgrade --install inference-svc helm/inference-svc/ -n ns-staging

# 4. Run tests
cd services/rule-engine && pytest tests/ --cov=rule_engine
cd services/normalizer  && pytest tests/ --cov=normalizer
cd services/anonymizer  && pytest tests/ --cov=anonymizer
cd services/inference-svc && pytest tests/ --cov=inference_svc

# 5. Train ML model
cd ml && python generate_synthetic_dataset.py && python train.py && python upload_model.py
```

## Contributors

- Andersson David Sánchez Méndez — DevOps / Infrastructure
- Cristian Santiago Pedraza Rodríguez — Backend / Microservices
- Jeisson David Sánchez Gómez — ML / Mobile / Observability
