FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --default-timeout=600 -r requirements.txt

COPY src/ ./src/

ENV PYTHONPATH=/app/src:/app
ENV PYTHONUNBUFFERED=1

RUN useradd --create-home appuser && chown -R appuser /app
USER appuser

EXPOSE 8084

CMD ["uvicorn", "api.server:api", "--host", "0.0.0.0", "--port", "8084", "--workers", "1"]
