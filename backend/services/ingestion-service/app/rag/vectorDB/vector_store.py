from app.rag.vectorDB.qdrantClient import qdrant_client
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
)

COLLECTION_NAME = "sinhala_books"

client = qdrant_client()


def create_collection():
    collections = client.get_collections()

    names = [
        c.name
        for c in collections.collections
    ]

    if COLLECTION_NAME not in names:
        client.create_collection(
            collection_name = COLLECTION_NAME,
            vectors_config = VectorParams(
                size=3072,
                distance = Distance.COSINE,
            ),
        )
        
def upload_chunks(chunks, vectors):
    points = []

    for chunk, vector in zip(chunks, vectors):
        points.append(
            PointStruct(
                id = chunk["id"],
                vector = vector,
                payload = {
                    "text": chunk["text"],
                    **chunk["metadata"],
                },
            )
        )

    client.upsert(
        collection_name = COLLECTION_NAME,
        points = points,
    )
    
    
def create_payload_indexes():
    client.create_payload_index(
        collection_name = COLLECTION_NAME,
        field_name = "source_file",
        field_schema = "keyword",
    )

    client.create_payload_index(
        collection_name = COLLECTION_NAME,
        field_name = "page_number",
        field_schema = "integer",
    )

    client.create_payload_index(
        collection_name = COLLECTION_NAME,
        field_name = "block_type",
        field_schema = "keyword",
    )