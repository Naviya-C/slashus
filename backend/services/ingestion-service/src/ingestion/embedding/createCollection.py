from config import load_env
from qdrant_client import QdrantClient, models

environ = load_env()
qdrant_api = environ['QDRANT_CLUSTER_API']
qdrant_url = environ['QDRANT_CLUSTER_ENDPOINT']

c = QdrantClient(
    url = qdrant_url,
    api_key = qdrant_api
)

NAME = "sinhala_books_v2"

c.create_collection(
    collection_name=NAME,
    vectors_config={
        "dense": models.VectorParams(size=1024, distance=models.Distance.COSINE),
    },
    sparse_vectors_config={
        "sparse": models.SparseVectorParams(
            index=models.SparseIndexParams(on_disk=False),
            modifier=models.Modifier.IDF, 
        ),
    },
)

# scope filters
c.create_payload_index(NAME, "source_file", models.PayloadSchemaType.KEYWORD)
c.create_payload_index(NAME, "page_number", models.PayloadSchemaType.INTEGER)
c.create_payload_index(NAME, "block_type", models.PayloadSchemaType.KEYWORD)  # was "content_type" — payload never wrote that key
c.create_payload_index(NAME, "user_id", models.PayloadSchemaType.KEYWORD)     # multi-tenant scoping
c.create_payload_index(NAME, "doc_id", models.PayloadSchemaType.KEYWORD)
c.create_payload_index(NAME, "lesson_title", models.PayloadSchemaType.KEYWORD)

# full-text, for topic-term matching
c.create_payload_index(
    NAME, "text",
    models.TextIndexParams(
        type="text",
        tokenizer=models.TokenizerType.WHITESPACE,
        min_token_len=2,
        lowercase=True,
    ),
)