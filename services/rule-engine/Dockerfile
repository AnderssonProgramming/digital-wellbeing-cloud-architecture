# ---- Builder stage ----
FROM python:3.11-slim AS builder
WORKDIR /build
COPY pyproject.toml .
RUN pip install --no-cache-dir build && pip install --no-cache-dir .
COPY rule_engine/ rule_engine/
COPY tests/ tests/
RUN pip install --no-cache-dir pytest pytest-cov && pytest tests/ --cov=rule_engine --cov-fail-under=80

# ---- Runtime stage ----
FROM python:3.11-slim AS runtime
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /build/rule_engine /app/rule_engine
USER appuser
EXPOSE 8001
CMD ["python", "-m", "uvicorn", "rule_engine.main:app", "--host", "0.0.0.0", "--port", "8001"]
