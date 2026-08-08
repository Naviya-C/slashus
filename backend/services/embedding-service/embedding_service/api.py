"""
---Thin health-check API for the embedding service.---

Run EXACTLY ONE instance of this service:
the sparse encoder writes a shared vocab file and is single-writer.
"""

from fastapi import FastAPI

app = FastAPI(title="embedding-service")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
