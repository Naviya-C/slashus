from app.rag.embedding.models import embedd_model_client


client = embedd_model_client()


def embed_texts(texts, batch_size=100):
    vectors = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]

        response = client.models.embed_content( 
            model="gemini-embedding-001",
            contents=batch
        )

        vectors.extend(
            emb.values
            for emb in response.embeddings
        )

    return vectors


def embed_query(query):
    response = client.models.embed_content(
        model="gemini-embedding-001",
        contents=query
    )

    return response.embeddings[0].values