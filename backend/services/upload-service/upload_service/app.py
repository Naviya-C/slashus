"""
upload_service/app.py
=====================

    POST /uploads          upload a PDF, mint doc_id, kick off ingestion
    GET  /user_documents   the caller's documents (sidebar)
    GET  /healthz          liveness

Identity comes from X-User-Id, which the gateway sets from a verified token.
This service is only reachable through the gateway (compose uses
`expose: 8002`, not `ports:`), so that header is trustworthy.

The list query filters on user_id. Document ids will appear in URLs, so any
future endpoint that takes a doc_id must filter on user_id too — otherwise an
authenticated caller who learns an id can reach someone else's file. The
gateway proved *who* they are; it did not prove the document is *theirs*.
"""

from __future__ import annotations

from dotenv import load_dotenv

load_dotenv()

import logging
import uuid
from datetime import datetime

import anyio
from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from contracts import DocUploaded
from storage import create_store, source_key

from .database.schema import Document
from .database.con import SessionLocal, get_db
from .messaging.producer import UploadPublisher

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

app = FastAPI(title="upload-service")

_store = create_store()
_publisher = UploadPublisher.from_env()

_PDF_MAGIC = b"%PDF-"
_MAX_BYTES = 100 * 1024 * 1024  # 100 MB guard
_MAX_NAME = 255  # matches Document.name's VARCHAR(255)


def current_user(x_user_id: str = Header(..., alias="X-User-Id")) -> uuid.UUID:
    """Resolve the caller from the gateway-injected header."""
    try:
        return uuid.UUID(x_user_id)
    except (ValueError, AttributeError):
        raise HTTPException(400, "invalid user")


class DocumentOut(BaseModel):
    """What the sidebar renders.

    storage_key is deliberately NOT exposed. It's an internal GCS path;
    publishing it invites clients to construct object URLs and couples the
    frontend to a storage layout you'll want to change.
    """

    doc_id: uuid.UUID
    name: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


@app.post("/uploads", status_code=202)
async def upload(
    file: UploadFile = File(...),
    user_id: uuid.UUID = Depends(current_user),
):
    data = await file.read()
    if len(data) > _MAX_BYTES:
        raise HTTPException(413, "file too large")
    if not data.startswith(_PDF_MAGIC):  # trust bytes, not the header
        raise HTTPException(415, "only PDF files are accepted")

    doc_uuid = uuid.uuid4()
    doc_id = str(doc_uuid)
    key = source_key(str(user_id), doc_id)

    name = (file.filename or "upload.pdf")[:_MAX_NAME]

    def _store_and_publish() -> None:
        # ORDER MATTERS.
        
        # 1. GCS first — if it fails, nothing else has happened.
        _store.put(key=key, data=data, content_type="application/pdf")

        # 2. DB row BEFORE the Kafka event. ingestion-service reacts to that
        with SessionLocal() as db:
            db.add(
                Document(
                    doc_id=doc_uuid, user_id=user_id, name=name, storage_key=key
                )
            )
            db.commit()

        # 3. Kafka last — the row exists, so any consumer can resolve doc_id.
        _publisher.publish(
            DocUploaded(
                doc_id=doc_id,
                user_id=str(user_id),
                source_name=name,
                storage_key=key,
            )
        )
        _publisher.flush()

    # offload blocking I/O so concurrent uploads don't serialize on the loop
    await anyio.to_thread.run_sync(_store_and_publish)

    log.info("accepted upload doc_id=%s user_id=%s (%d bytes)", doc_id, user_id, len(data))
    return {"doc_id": doc_id, "name": name, "status": "accepted"}


@app.get("/api/v1/user_documents", response_model=list[DocumentOut])
def user_documents(
    user_id: uuid.UUID = Depends(current_user),
    db: Session = Depends(get_db),
):
    """The sidebar. Newest first — matches idx_documents_user_created.

    Unpaginated on purpose for the MVP. Add limit/offset once a user can
    plausibly have hundreds of documents; the index already supports it.
    """
    return db.scalars(
        select(Document)
        .where(Document.user_id == user_id)
        .order_by(Document.created_at.desc())
    ).all()


@app.get("/healthz")
def healthz():
    """Liveness only — deliberately does not touch Postgres, GCS, or Kafka.

    A readiness probe that calls out to dependencies turns a brief outage into
    a container restart loop.
    """
    return {"ok": True}
