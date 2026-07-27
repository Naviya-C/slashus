"""
storage/paths.py
================

Helpers for generating logical object keys.

These keys are backend-agnostic and are used by every storage
implementation (Local, GCS, S3, etc.).

Never return absolute filesystem paths or provider-specific URLs.
"""

from __future__ import annotations


SOURCE_FILENAME = "source.pdf"


def source_key(user_id: str, doc_id: str) -> str:
    """
    Return the storage key for the uploaded source PDF.

    Example
    -------
    >>> source_key("user123", "doc456")
    'user123/doc456/source.pdf'
    """
    return f"{user_id}/{doc_id}/{SOURCE_FILENAME}"


def image_key(
    user_id: str,
    doc_id: str,
    image_id: str,
    extension: str,
) -> str:
    """
    Return the storage key for an extracted image.

    Example
    -------
    >>> image_key("user123", "doc456", "img001", "png")
    'user123/doc456/images/img001.png'
    """
    extension = extension.lstrip(".")
    return f"{user_id}/{doc_id}/images/{image_id}.{extension}"


def table_key(
    user_id: str,
    doc_id: str,
    table_id: str,
) -> str:
    """
    Return the storage key for an extracted table.

    Example
    -------
    >>> table_key("user123", "doc456", "tbl001")
    'user123/doc456/tables/tbl001.json'
    """
    return f"{user_id}/{doc_id}/tables/{table_id}.json"


def metadata_key(
    user_id: str,
    doc_id: str,
) -> str:
    """
    Return the storage key for document metadata.

    Example
    -------
    >>> metadata_key("user123", "doc456")
    'user123/doc456/metadata.json'
    """
    return f"{user_id}/{doc_id}/metadata.json"