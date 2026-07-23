"""Orchestrator graph (LangGraph).

    START -> route -> ┬ greeting ┐
                      ├ casual  ─┤
                      └ agents ──┴-> respond -> persist -> END

The `agents` node runs the router-chosen step names against the agent REGISTRY
— no hardcoded agent knowledge. New agents appear once registered + mapped in
the router. The graph is fixed; capabilities grow.
"""

from __future__ import annotations

import json
import logging
from uuid import UUID

from langgraph.graph import END, START, StateGraph

from agents import AgentContext, build_registry
from core.llm import LLMClient
from events import Event, build_event_bus
from orchestrator.graph.state import GraphState
from orchestrator.nodes import casual_node, greeting_node
from orchestrator.router import INTENT_STEPS, Intent, Router
from state import ConversationState, Turn, build_state

logger = logging.getLogger(__name__)
 

class Orchestrator:
    def __init__(self, router = None, registry = None, state = None, llm = None, event_bus = None) -> None:
        self._llm = llm or LLMClient()
        self._router = router or Router(self._llm)
        self._registry = registry if registry is not None else build_registry()
        self._state = state or build_state()
        self._bus = event_bus or build_event_bus()
        self._graph = self._build()

    def _build(self):
        g = StateGraph(GraphState)
        
        g.add_node("route", self._route)
        g.add_node("greeting", self._greeting)
        g.add_node("casual", self._casual)
        g.add_node("agents", self._agents)
        g.add_node("respond", self._respond)
        g.add_node("persist", self._persist)
        
        g.add_edge(START, "route")
        g.add_conditional_edges("route", self._dispatch,
                                {"greeting": "greeting", "casual": "casual", "agents": "agents"})
        g.add_edge("greeting", "persist")
        g.add_edge("casual", "persist")
        g.add_edge("agents", "respond")
        g.add_edge("respond", "persist")
        g.add_edge("persist", END)
        
        return g.compile()

    def _route(self, s: GraphState) -> GraphState:
        r = self._router.route(s["message"])
        intent, steps = r.intent, r.steps
        data: dict = {}

        # Continuation ("give me more"). "more" is a weak keyword, so only treat
        # it as a continuation when this session ACTUALLY has prior questions to
        # build on — otherwise fall back to a normal generate. This also keeps
        # users isolated: prior questions are read per session_id, so one user's
        # "more" never pulls another user's questions.
        if intent == Intent.GENERATE_MORE:
            prior = self._load_prior_questions(s["user_id"], s["session_id"])
            if prior:
                # reuse the chunks from the previous generate turn (skip retrieval)
                prior_chunks = self._load_prior_chunks(s["user_id"], s["session_id"])
                data = {"prior_questions": prior, "chunks": prior_chunks}
            else:
                # nothing to continue -> behave like a fresh generate
                intent = Intent.GENERATE
                steps = INTENT_STEPS[Intent.GENERATE]

        logger.info("route: intent = %s method = %s steps = %s", intent.value, r.method, steps)
        return {"intent": intent.value, "steps": steps, "method": r.method,
                "data": data, "errors": []}

    # --- continuation state helpers (per session_id → multi-user safe) ---

    def _load_prior_questions(self, user_id: UUID, session_id: str) -> list[dict]:
        raw = self._state.get_scratch(user_id, session_id, "last_questions")
        if not raw:
            return []
        try:
            return json.loads(raw)
        except (ValueError, TypeError):
            return []

    def _load_prior_chunks(self, user_id: UUID, session_id: str) -> list[dict]:
        raw = self._state.get_scratch(user_id, session_id, "last_chunks")
        if not raw:
            return []
        try:
            return json.loads(raw)
        except (ValueError, TypeError):
            return []

    def _save_generation(self, user_id: UUID, session_id: str, data: dict) -> None:
        # Save the FULL running set so the next "more" avoids everything shown.
        full = data.get("all_questions", data.get("questions", []))
        if full:
            self._state.set_scratch(user_id, session_id, "last_questions", json.dumps(full, ensure_ascii = False))
        if data.get("chunks"):
            self._state.set_scratch(user_id, session_id, "last_chunks", json.dumps(data["chunks"], ensure_ascii = False))

    def _dispatch(self, s: GraphState) -> str:
        if s["intent"] == Intent.GREETING.value:
            return "greeting"
        if s["intent"] == Intent.CASUAL.value:
            return "casual"
        return "agents"

    def _greeting(self, s: GraphState) -> GraphState:
        return {"reply": greeting_node(s["message"])}

    def _casual(self, s: GraphState) -> GraphState:
        return {"reply": casual_node(s["message"])}

    def _agents(self, s: GraphState) -> GraphState:
        ctx = AgentContext(query = s["message"], user_id = s["user_id"], session_id = s["session_id"], data = dict(s.get("data", {})))
        for step in s.get("steps", []):
            agent = self._registry.get(step)
            if agent is None:
                logger.warning("No agent registered for step %r", step)
                ctx.errors.append(f"missing_agent:{step}")
                continue
            try:
                agent.run(ctx)
                # Event-driven seam: each completed step emits a domain event.
                # Today handled in-process; future = published to a queue and a
                # gateway/saga drives the next step. (see events/bus.py)
                self._bus.publish(Event(
                    type = f"{step}.completed",
                    session_id = s["session_id"],
                    payload = {"keys": list(ctx.data.keys())},
                ))
            except Exception:
                logger.exception("Agent %r crashed", step)
                ctx.errors.append(f"crashed:{step}")

        # Persist the generated questions (running set) + chunks for this
        # session, so a follow-up "give me more" continues from here.
        if ctx.data.get("artifact") == "questions":
            self._save_generation(s["session_id"], ctx.data)

        return {"data": ctx.data, "errors": ctx.errors}

    def _respond(self, s: GraphState) -> GraphState:
        d = s.get("data", {})
        artifact = d.get("artifact")
        if artifact == "questions":
            reply = f"Generated {len(d.get('questions', []))} question(s)."
        elif artifact == "summary":
            reply = "Summary ready."
        elif artifact == "flashcards":
            reply = f"Generated {len(d.get('flashcards', []))} flashcard(s)."
        elif artifact == "explanation":
            reply = "Explanation ready."
        elif "marking" in d and d["marking"]:
            m = d["marking"]
            reply = f"Graded: {m['total_score']:.1f}/{m['total_max']:.1f}."
        elif "chunks" in d:
            reply = f"Found {len(d['chunks'])} relevant passage(s)."
        elif d.get("note"):
            reply = d["note"]
        else:
            reply = "Done."
        return {"reply": reply}

    def _persist(self, s: GraphState) -> GraphState:
        self._state.record(Turn(
            session_id = s["session_id"], user_id=s["user_id"], user_message = s["message"],
            intent = s.get("intent", ""), assistant_message = s.get("reply", ""),
            metadata = {"method": s.get("method", ""), "errors": s.get("errors", [])},
        ))
        return {}

    def run(self, message: str, user_id: UUID, session_id: str = "default") -> dict:
        final = self._graph.invoke({"session_id": session_id, "message": message, "data": {}})
        return {
            "session_id": session_id,
            "user_id": user_id,
            "intent": final.get("intent", ""),
            "reply": final.get("reply", ""),
            "data": final.get("data", {}),
            "errors": final.get("errors", []),
        }
