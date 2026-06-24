from app.rag.embedding.models import embedd_model_client

client = embedd_model_client()

def generate_answer(prompt: str):

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )

    return response.text

