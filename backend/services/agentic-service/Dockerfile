FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --default-timeout=600 -r requirements.txt

COPY src/ ./src/
COPY database/ ./database/

ENV PYTHONPATH=/app/src:/app
ENV PYTHONUNBUFFERED=1

RUN useradd --create-home appuser && chown -R appuser /app
USER appuser

EXPOSE 8084

# No BGE-M3 here any more — embedding-service owns the model. This image is
# now a few hundred MB rather than several GB, and starts in seconds rather
# than waiting on a 2 GB model load.
#
# One worker: the orchestrator holds no shared state, but scaling belongs
# behind the gateway as replicas, not as workers inside one container.
CMD ["uvicorn", "api.server:api", "--host", "0.0.0.0", "--port", "8084", "--workers", "1"]
