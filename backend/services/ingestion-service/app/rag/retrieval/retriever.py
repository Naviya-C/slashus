from app.rag.embedding.embedder import embed_query
from app.rag.vectorDB.vector_store import client
from qdrant_client.models import Filter

COLLECTION_NAME = "sinhala_books"


def retrieve(
    question: str,
    top_k: int = 5,
):
    query_vector = embed_query(question)

    response = client.query_points(
        collection_name = COLLECTION_NAME,
        query = query_vector,
        limit = top_k,
    )

    return response.points