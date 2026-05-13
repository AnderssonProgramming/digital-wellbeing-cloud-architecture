# Runbook — Plataforma CVS

Guía de operación punto a punto del proyecto. Asume que la persona que la
sigue tiene una terminal con permisos de administrador y conexión a
Internet, y que clonó el repositorio.

> Convención: los comandos se asumen ejecutados desde la raíz del repo.

---

## 0. Prerrequisitos

| Herramienta | Versión mínima | Cómo lo verifico |
|---|---|---|
| Python | 3.11 | `python --version` |
| Docker Desktop | 24 | `docker --version` |
| `kubectl` | 1.29 | `kubectl version --client` |
| Helm | 3.13 | `helm version` |
| Terraform | 1.6 | `terraform version` |
| AWS CLI | 2.x | `aws --version` |
| `pdflatex` (MiKTeX o TeX Live) | reciente | `pdflatex --version` |

> **No pegues credenciales AWS en chats ni en el repo.** Configúralas con
> `aws configure sso` (lo recomendado para Cloud Labs) o copia el bloque
> `[default]` en `~/.aws/credentials` solo en tu máquina local.

---

## 1. Setup local de Python

```bash
python -m venv .venv
.venv\Scripts\activate              # Windows PowerShell / Bash
pip install -U pip
pip install -r services/rule-engine/requirements.txt
pip install -r services/normalizer/requirements.txt
pip install -r services/anonymizer/requirements.txt
pip install -r services/inference-svc/requirements.txt
pip install -r ml/requirements.txt
```

(Si los servicios traen `pyproject.toml` en lugar de `requirements.txt`,
basta con `pip install -e services/<nombre>` para cada uno.)

---

## 2. Generar el dataset, entrenar el modelo y producir las figuras

```bash
# 2.1 Dataset sintético calibrado con literatura clínica (50.000 filas)
python ml/generate_synthetic_dataset.py
# Output: ml/data/synthetic_dataset.csv

# 2.2 Entrenamiento con CV de 5 folds + assert de SLOs
python ml/train.py
# Output: ml/results/model.joblib + model_metadata.json
# Esperado: F1 macro ~0,85, AUC-ROC ~0,89

# 2.3 Generar las 5 figuras del paper (PDF)
python ml/plots.py
# Output: paper/figures/{roc_curve, feature_importance, score_distribution,
#                       dataset_overview, confusion_matrix}.pdf
```

Lo que estás validando aquí: si esto pasa sin errores, los componentes
de ML del prototipo están funcionales de punta a punta.

---

## 3. Tests unitarios y auditoría de privacidad

```bash
# 3.1 Tests por microservicio
( cd services/rule-engine    && python -m pytest tests/ -q )
( cd services/normalizer     && python -m pytest tests/ -q )
( cd services/anonymizer     && python -m pytest tests/ -q )
( cd services/inference-svc  && python -m pytest tests/ -q )

# 3.2 Tests del pipeline ML
python -m pytest ml/tests/ -q

# 3.3 Auditoría automática de privacidad (5 pruebas)
python tests/privacy_audit.py
# Esperado: "Privacy Audit Results: 5/5 PASS"
```

---

## 4. Levantar el stack localmente con `docker compose`

Esta es la **demo funcional para sustentación**: levanta Kafka, InfluxDB,
los 4 microservicios FastAPI, Prometheus y Grafana en una sola máquina.

> El `docker-compose.yml` de la raíz ya está listo; no hay que editar
> nada. Lo único que se requiere es Docker Desktop arrancado.

### 4.1 Levantar el stack

```powershell
# Desde la raíz del repo
docker compose up --build -d
```

La primera vez tarda 3-5 min porque construye las cuatro imágenes. En
los siguientes arranques baja a < 30 s.

### 4.2 Verificar que todos los contenedores están "healthy"

```powershell
docker compose ps
```

Debes ver ocho contenedores `Up` (`cvs-kafka` e `cvs-influxdb` con la
marca `healthy`).

### 4.3 Smoke test end-to-end

```powershell
python tests/smoke_test.py
```

Resultado esperado (probado el 2026-05-08 sobre este mismo
`docker-compose.yml`):

```text
[PASS] rule-engine   health: 200
[PASS] normalizer    health: 200
[PASS] anonymizer    health: 200
[PASS] inference-svc health: 200
[PASS] Ingest: 202 Accepted
Waiting 30s for pipeline processing...
[PASS] Risk score: 0.6821 (level: MEDIUM)
```

### 4.4 Endpoints útiles para la sustentación

| Servicio | URL | Uso en demo |
| --- | --- | --- |
| `inference-svc` Swagger | <http://localhost:8004/docs> | API pública del prototipo |
| `inference-svc` ingest | `POST /v1/telemetry/ingest` en 8004 | Mostrar el flujo de ingestión |
| `inference-svc` score | `GET /v1/scores/{uuid}/current` en 8004 | Mostrar el puntaje |
| InfluxDB UI | <http://localhost:8086> | Login `admin / admin12345`, ver bucket `cvs-telemetry` |
| Prometheus | <http://localhost:9091> | Buscar `cvs_*` en el explorador |
| Grafana | <http://localhost:3000> | Login `admin / admin`, importar JSON de `grafana/dashboards/` |
| Health checks | `:8001/v1/health` … `:8004/v1/health` | Cada microservicio responde 200 |

### 4.5 Importar los tableros de Grafana

```powershell
# Crear datasource Prometheus
curl -X POST -u admin:admin -H "Content-Type: application/json" `
  -d '{\"name\":\"Prometheus\",\"type\":\"prometheus\",\"url\":\"http://prometheus:9090\",\"access\":\"proxy\",\"isDefault\":true}' `
  http://localhost:3000/api/datasources

# Importar los 3 dashboards JSON del repo
foreach ($f in Get-ChildItem grafana/dashboards/*.json) {
  curl -X POST -u admin:admin -H "Content-Type: application/json" `
    --data-binary "@$($f.FullName)" `
    http://localhost:3000/api/dashboards/db
}
```

### 4.6 Apagar el stack

```powershell
docker compose down       # detiene contenedores, conserva volúmenes
docker compose down -v    # también borra los volúmenes (InfluxDB, Grafana)
```

---

## 5. Despliegue en AWS

> **Lectura honesta del estado actual.** El Terraform en `infra/terraform/`
> está escrito (EKS + MSK + S3 versionado) pero **no funciona en el AWS
> Academy Learner Lab** que se nos asigna como Cloud Lab del curso. La
> política `voc-cancel-cred` deniega `iam:CreateRole`, `eks:*`, `msk:*`,
> `ecr:*`, `s3:CreateBucket` y `ec2:CreateSecurityGroup`. Confirmado por
> intento real (`terraform apply` → 4 errores `AccessDenied`). En una
> cuenta AWS sin esa restricción los comandos de abajo sí corren.
>
> **Para sustentar el proyecto la demo va por `docker compose`**
> (sección 4): el stack está corriendo, el smoke test pasa y los seis
> diagramas del paper documentan la arquitectura objetivo en AWS.
> Sustentar EKS + MSK requeriría una cuenta AWS personal con permisos
> completos, fuera del alcance del semestre.

### 5.1 Configurar credenciales (cuenta NO restringida)

```bash
aws configure sso              # opción recomendada
# o
aws configure                  # access key + secret + region

aws sts get-caller-identity    # debe devolver tu Account real
```

> **Nunca pegues credenciales en chats, issues o commits.** Si
> sospechas que se filtraron, en un Cloud Lab basta con cerrar y
> reabrir la sesión; en cuenta normal, rota la access key.

### 5.2 Provisionar la infraestructura

```bash
cd infra/terraform
terraform init
terraform plan -out plan.tfplan
terraform apply plan.tfplan
# Crea: VPC, EKS (3 node groups), MSK (3 brokers), S3 versionado
# Tiempo: 15-20 min
```

### 5.3 Conectar kubectl al EKS

```bash
aws eks update-kubeconfig --region us-east-1 --name cvs-cloud-platform
kubectl get nodes
```

### 5.4 Aplicar manifiestos y desplegar con Helm

```bash
cd ../../
kubectl apply -f k8s/namespaces.yaml
kubectl apply -f k8s/rbac.yaml
kubectl apply -f k8s/network-policies.yaml

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=us-east-1
ECR_BASE=$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ECR_BASE
for svc in rule-engine normalizer anonymizer inference-svc; do
  aws ecr create-repository --repository-name cvs/$svc 2>/dev/null || true
  docker build -t $ECR_BASE/cvs/$svc:1.0.0 services/$svc
  docker push $ECR_BASE/cvs/$svc:1.0.0
done

for svc in rule-engine normalizer anonymizer inference-svc; do
  case $svc in
    inference-svc) NS=ns-data-ml ;;
    *)             NS=ns-processing ;;
  esac
  helm upgrade --install $svc helm/$svc/ -n $NS \
    --set image.repository=$ECR_BASE/cvs/$svc \
    --set image.tag=1.0.0
done
```

### 5.5 Subir el modelo entrenado a S3

```bash
export S3_MODEL_BUCKET=$(terraform -chdir=infra/terraform output -raw model_bucket_name)
python ml/upload_model.py
```

### 5.6 Apagar para no gastar crédito

```bash
cd infra/terraform
terraform destroy
```

---

## 6. Pruebas de carga (JMeter)

```bash
# Apuntar la prueba a la URL del API (local con port-forward o ALB en AWS)
jmeter -n -t tests/load/cvs_load_test.jmx \
       -Jhost=localhost -Jport=8080 \
       -l results/load.jtl \
       -e -o results/load-report
# Output: HTML con percentiles P50, P95, P99
```

---

## 7. Compilar el paper

```bash
cd paper

# Pasada 1: genera .aux con referencias
pdflatex -interaction=nonstopmode paper-cvs-es.tex

# Pasada 2: resuelve referencias cruzadas (figuras, tablas, citas)
pdflatex -interaction=nonstopmode paper-cvs-es.tex

# Pasada 3: cierra la consistencia (numeración final)
pdflatex -interaction=nonstopmode paper-cvs-es.tex

# Resultado: paper-cvs-es.pdf (21 páginas)
```

> Si cambiaste el dataset o reentrenaste el modelo, antes de compilar
> regenera las figuras con `python ml/plots.py` y revisa que los
> números en `Sección X — Resultados` siguen coincidiendo con
> `ml/results/model_metadata.json`.

---

## 8. Checklist final antes de la presentación

- [ ] `python ml/generate_synthetic_dataset.py` corre sin errores.
- [ ] `python ml/train.py` reporta F1 ≥ 0,75 y AUC ≥ 0,80.
- [ ] `python ml/plots.py` genera 5 PDFs en `paper/figures/`.
- [ ] `python tests/privacy_audit.py` reporta `5/5 PASS`.
- [ ] Todos los `pytest` por microservicio pasan.
- [ ] El paper compila a 16 páginas sin warnings de citas.
- [ ] El README muestra los 6 diagramas profesionales (no Mermaid).
- [ ] No hay credenciales AWS en el repo (`git grep -E
      "AKIA|ASIA|aws_access_key_id"` debe salir vacío).
- [ ] `terraform plan` corre limpio (no destruye recursos por accidente).
- [ ] Los stubs honestos están listados en la sección de Discusión del
      paper (SQLCipher en mobile y la cola larga del dataset sintético).
