from fastapi import APIRouter
from pydantic import BaseModel

from app.rag.retrieval.query_pipeline import ask

router = APIRouter()


class ChatRequest(BaseModel):
    question: str


@router.post("/chat")
def chat(request: ChatRequest):
    result = ask(request.question)

    answer = result["answer"]
    points = result["sources"]

    sources = [
        {
            "page_number": p.payload["page_number"],
            "text": p.payload["text"],
            "source_file": p.payload["source_file"],
        }
        for p in points
    ]

    return {
        "answer": answer, 
        "sources": sources,
    }