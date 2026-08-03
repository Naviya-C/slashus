"""Vector search — a thin gRPC client onto embedding-service."""

from vectorstore.grpc_client import GrpcVectorClient, build_vector_client
from vectorstore.schemas import SearchHit, SearchRequest, SearchResponse

# Kept as an alias so the retrieval agent's type hint still resolves.
VectorClient = GrpcVectorClient

__all__ = [
    "SearchHit", "SearchRequest", "SearchResponse",
    "GrpcVectorClient", "VectorClient", "build_vector_client",
]
