FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir .
COPY anonymizer/ anonymizer/

RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
USER appuser

EXPOSE 8003
CMD ["python", "-m", "uvicorn", "anonymizer.main:app", "--host", "0.0.0.0", "--port", "8003"]
