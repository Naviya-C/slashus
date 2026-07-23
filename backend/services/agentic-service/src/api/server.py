"""
    FastAPI HTTP API + CLI.

    CLI:  python -m src.api.server "<message>"
    API:  uvicorn src.api.server:api --port 8080 --reload (path could change the terminal location.)
        POST /chat      {"message": "...", "session_id": "abc"}
        POST /mark      {"session_id": "abc", "submission": [ ... ]}
        GET  /agents    -> registered agents
        GET  /languages -> vector databases available

    NOTE (future event-driven): today /chat runs the orchestrator synchronously.
    When moving to the API-gateway / event-driven model, /chat would instead
    publish a UserQueryReceived event and return a job id; a websocket or polling
    endpoint would stream results. The orchestrator already emits step events
    (events/bus.py), so that migration doesn't touch agent code.
"""

from __future__ import annotations

import logging
import sys
from uuid import UUID

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(name)s %(levelname)s %(message)s")

from orchestrator import Orchestrator  

_orch: Orchestrator | None = None


def get_orchestrator() -> Orchestrator:
    global _orch
    if _orch is None:
        _orch = Orchestrator()
    return _orch


try: 
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel

    api = FastAPI(title = "Agentic Study System")
    api.add_middleware(
        CORSMiddleware, 
        allow_origins = ["*"], 
        allow_methods = ["*"], 
        allow_headers = ["*"],
    )

    class ChatRequest(BaseModel):
        message: str
        session_id: str = "default"

    class MarkRequest(BaseModel):
        session_id: str = "default"
        submission: list[dict]

    @api.post("/chat")
    def chat(req: ChatRequest, x_user_id: UUID):
        return get_orchestrator().run(req.message, req.session_id)

    @api.post("/mark")
    def mark(req: MarkRequest):
        # Directly invoke the marking flow by seeding a submission.
        orch = get_orchestrator()
        # Route as a mark intent with the submission preloaded via a synthetic
        # message; the marker reads ctx.data["submission"].
        from agents import AgentContext
        from agents.marker import MarkerAgent
        ctx = AgentContext(query="mark", session_id=req.session_id, data={"submission": req.submission})
        MarkerAgent().run(ctx)
        return {"session_id": req.session_id, "data": ctx.data, "errors": ctx.errors}

    @api.get("/agents")
    def agents():
        from agents import registered_names
        return {"registered_agents": registered_names()}

    @api.get("/languages")
    def languages():
        from vectorstore import build_vector_client
        return {"languages": build_vector_client().languages()}
except ImportError:
    api = None


if __name__ == "__main__":
    message = " ".join(sys.argv[1:]) or "ආයුබෝවන්"
    result = get_orchestrator().run(message, session_id="cli")
    print(f"\nintent: {result['intent']}\nreply : {result['reply']}\n")
    data = result["data"]
    for i, q in enumerate(data.get("questions", []), 1):
        print(f"{i}. [{q['type']}] {q['question']}")
        for o in q.get("options", []):
            print(f"     {o['label']}) {o['text']}")
        if q.get("answer"):
            print(f"     → {q['answer']}")
        print()
    if data.get("summary"): print("SUMMARY:", data["summary"][:400])
    if data.get("explanation"): print("EXPLANATION:", data["explanation"][:400])
    for c in data.get("flashcards", []):
        print(f"  [{c['front']}] → {c['back']}")
