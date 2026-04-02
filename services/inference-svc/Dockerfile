FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir .
COPY inference_svc/ inference_svc/

RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
USER appuser

EXPOSE 8004
CMD ["python", "-m", "uvicorn", "inference_svc.main:app", "--host", "0.0.0.0", "--port", "8004"]
