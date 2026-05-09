FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml .
COPY rule_engine/ rule_engine/
RUN pip install --no-cache-dir . \
 && addgroup --system appgroup \
 && adduser  --system --ingroup appgroup appuser
USER appuser

EXPOSE 8001
CMD ["python", "-m", "uvicorn", "rule_engine.main:app", "--host", "0.0.0.0", "--port", "8001"]
