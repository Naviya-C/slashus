from app.rag.retrieval.retriever import retrieve
from app.rag.retrieval.promptTemplate import RAG_PROMPT
from app.rag.retrieval.generator import generate_answer

def ask(question: str):
    points = retrieve(
        question,
        top_k=5,
    )

    context = "\n\n".join(
        point.payload["text"]
        for point in points
    )

    prompt = RAG_PROMPT.invoke(
        {
            "context": context,
            "question": question,
        }
    )

    answer = generate_answer(
        prompt.to_string()
    )

    return {
        "answer": answer,
        "sources": points,
    }