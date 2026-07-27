"""
ports/storage.py
================

PURPOSE
-------
The seam between the pipeline and wherever bytes live. The pipeline stores and
retrieves through THIS interface, never a specific backend -- so we run locally
against the filesystem now and swap in cloud object storage later without
touching pipeline code.

THE CONTRACT
------------
    put(key, data) -> str        store bytes at key, return a locator (path/url)
    get(key) -> bytes            read bytes back; raises StorageKeyNotFound
    exists(key) -> bool          cheap presence check, no download
    url(key) -> str              a locator to access it (file path / signed URL)
    delete_prefix(prefix) -> int delete everything under a prefix, return count

Every adapter must implement ALL of these with the SAME failure behaviour.
A method that exists on one adapter but not another defeats the point of the
port: code works on cloud and AttributeErrors on local, or vice versa.

WHY exists() IS PART OF THE CONTRACT
------------------------------------
Some keys are legitimately absent. The sparse-vocab loader hits this on the
very first ingestion run -- there is no vocab yet, and that is a normal state,
not an error. Callers need to branch on it without catching exceptions.

KEY CONVENTION (per-user isolation)
-----------------------------------
Keys are user-prefixed so tenants never share storage and deletion is a single
prefix wipe:

    {user_id}/{doc_id}/images/{image_id}.{ext}    <- image_key()
    vocab/{collection}.json                       <- shared build artifact

Note the vocab is deliberately NOT per user: it is a property of the Qdrant
collection (all users' points are scored against it), not of a person.
"""

from __future__ import annotations

from typing import Protocol


class StorageKeyNotFound(KeyError):
    """Raised by get() when a key does not exist.

    Defined HERE, in the port, not in one adapter -- every backend raises this
    same type so callers can handle a missing key without knowing (or caring)
    whether they are talking to GCS or the local filesystem.
    """
 

class Storage(Protocol):
    def put(self, key: str, data: bytes) -> str: ...
    def get(self, key: str) -> bytes: ...
    def exists(self, key: str) -> bool: ...
    def url(self, key: str) -> str: ...
    def delete_prefix(self, prefix: str) -> int: ...


def image_key(user_id: str, doc_id: str, image_id: str, ext: str) -> str:
    """Build the per-user storage key for an image (shared by all adapters)."""
    ext = ext.lower().lstrip(".")
    return f"{user_id}/{doc_id}/images/{image_id}.{ext}"


def vocab_key(collection: str) -> str:
    """Build the key for a collection's sparse vocab.

    Shared across users by design: the vocab maps tokens to the sparse indices
    stored in that collection's points, so index-time and query-time must load
    the identical file or retrieval silently returns garbage.
    """
    return f"vocab/{collection}.json"