"""
upload_service/app.py
=====================

The user-facing edge of the pipeline.

    POST /uploads   (multipart: file + user_id)
      -> validate it's a PDF
      -> mint doc_id (uuid4)
      -> store bytes at {user_id}/{doc_id}/source.pdf   (off the event loop)
      -> emit doc.uploaded                              (off the event loop)
      -> 202 { doc_id }   (returns immediately; ingestion runs async)

Concurrency: the GCS upload and Kafka flush are BLOCKING calls, run in a worker
thread via anyio.to_thread so the event loop stays free and many uploads are
handled at once.

user_id is accepted as a form field here. In production it should come from a
gateway-verified token (header X-User-Id), NOT the raw client — the GCS key is
built from user_id and is trusted.
"""

from __future__ import annotations

# load .env before anything reads os.environ (ObjectStore.from_env runs at import)
from dotenv import load_dotenv
load_dotenv()

import logging
import uuid

import anyio
from fastapi import FastAPI, File, Form, HTTPException, UploadFile

from contracts import DocUploaded
from storage import create_store, source_key
from .messaging.producer import UploadPublisher

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

app = FastAPI(title="upload-service")

_store = create_store()
_publisher = UploadPublisher.from_env()

_PDF_MAGIC = b"%PDF-"
_MAX_BYTES = 100 * 1024 * 1024   # 100 MB guard


def _is_uuid(s: str) -> bool:
    try:
        uuid.UUID(s)
        return True
    except (ValueError, AttributeError):
        return False


@app.post("/uploads", status_code=202)
async def upload(file: UploadFile = File(...), user_id: str = Form(...)):
    if not _is_uuid(user_id):
        raise HTTPException(422, "user_id must be a uuid")

    data = await file.read()
    if len(data) > _MAX_BYTES:
        raise HTTPException(413, "file too large")
    if not data.startswith(_PDF_MAGIC):          # trust bytes, not the header
        raise HTTPException(415, "only PDF files are accepted")
 
    doc_id = str(uuid.uuid4())
    key = source_key(user_id, doc_id)

    def _store_and_publish() -> None:
        _store.put(key=key, data=data, content_type="application/pdf")
        log.info("PDF stored")
        log.info("Publishing DocUploaded event")
        _publisher.publish(DocUploaded(
            doc_id=doc_id,
            user_id=user_id,
            source_name=file.filename or "upload.pdf",
            storage_key=key,
        ))
        
        log.info("Flushing producer")
        _publisher.flush()
        log.info("Done")

    # offload blocking I/O so concurrent uploads don't serialize on the event loop
    await anyio.to_thread.run_sync(_store_and_publish)

    log.info("accepted upload doc_id=%s user_id=%s (%d bytes)", doc_id, user_id, len(data))
    return {"doc_id": doc_id, "user_id": user_id, "status": "accepted"}


@app.get("/healthz")
def healthz():
    return {"ok": True}
