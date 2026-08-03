"""Orchestrator graph (LangGraph).

    START -> route -> ┬ greeting ┐
                      ├ casual  ─┤
                      └ agents ──┴-> respond -> END

The `agents` node runs the router-chosen step names against the agent REGISTRY
— no hardcoded agent knowledge. New agents appear once registered and mapped
in INTENT_STEPS. The graph is fixed; capabilities grow.

Persistence moved OUT of the graph. The API writes turns via Repository after
shaping the response, because only the API knows the final reply text and the
practice_set_id that the turn should link to. Persisting inside the graph
meant writing a turn the API then had to update.
"""

from __future__ import annotations

import logging
from uuid import UUID

from langgraph.graph import END, START, StateGraph

from agents import AgentContext, build_registry
from core.config import settings
from core.llm.qwen import QwenClient
from events import Event, build_event_bus
from orchestrator.graph.state import GraphState
from orchestrator.nodes import casual_node, greeting_node
from orchestrator.router import INTENT_STEPS, Intent, Router
from state import build_scratch

logger = logging.getLogger(__name__)


class Orchestrator:
    def __init__(self, router=None, registry=None, scratch=None,
                 llm=None, event_bus=None, repo=None) -> None:
        self._llm = llm or QwenClient()
        self._router = router or Router(self._llm)
        self._registry = registry if registry is not None else build_registry(repo=repo)
        self._scratch = scratch or build_scratch()
        self._bus = event_bus or build_event_bus()
        self._graph = self._build()


    def _build(self):
        g = StateGraph(GraphState)

        g.add_node("route", self._route)
        g.add_node("greeting", self._greeting)
        g.add_node("casual", self._casual)
        g.add_node("agents", self._agents)
        g.add_node("respond", self._respond)

        g.add_edge(START, "route")
        g.add_conditional_edges(
            "route", self._dispatch,
            {"greeting": "greeting", "casual": "casual",
             "agents": "agents", "blocked": "respond"},
        )
        g.add_edge("greeting", END)
        g.add_edge("casual", END)
        g.add_edge("agents", "respond")
        g.add_edge("respond", END)

        return g.compile()
    

    def _route(self, s: GraphState) -> GraphState:
        r = self._router.route(s["message"])
        intent, steps = r.intent, r.steps
        data: dict = {"doc_ids": s.get("doc_ids", [])}

        if intent == Intent.GENERATE_MORE:
            prior = self._scratch.get(s["user_id"], s["session_id"], "last_questions")
            chunks = self._scratch.get(s["user_id"], s["session_id"], "last_chunks")
            if prior and chunks:
                data |= {"previous_questions": prior, "chunks": chunks}
            else:
                intent, steps = Intent.GENERATE, INTENT_STEPS[Intent.GENERATE]

        logger.info("route: intent=%s method=%s steps=%s", intent.value, r.method, steps)

        return {"intent": intent.value, "steps": steps, "method": r.method,
                "data": data, "errors": [], "reason": None}

    def _dispatch(self, s: GraphState) -> str:
        if s.get("reason"):
            return "blocked"
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
        ctx = AgentContext(
            query=s["message"],
            user_id=s["user_id"],
            session_id=s["session_id"],
            data=dict(s.get("data", {})),
        )

        for step in s.get("steps", []):
            agent = self._registry.get(step)
            if agent is None:
                logger.warning("no agent registered for step %r", step)
                ctx.errors.append(f"missing_agent:{step}")
                continue
            
            try:
                agent.run(ctx)
                self._bus.publish(Event(
                    type=f"{step}.completed",
                    session_id=s["session_id"],
                    payload={"keys": list(ctx.data.keys())},
                ))
            except Exception:
                logger.exception("agent %r crashed", step)
                ctx.errors.append(f"crashed:{step}")
                break
            
        if ctx.errors:
            logger.error("agent chain failed: %s", ctx.errors)
            return {"data": ctx.data, "errors": ctx.errors, "reason": None}
        
        if "retrieve" in s.get("steps", []) and not ctx.data.get("retrieved_count"):
            return {"data": ctx.data, "errors": ctx.errors, "reason": "no_relevant"}
        
        if ctx.data.get("grounded") is False:
            return {"data": ctx.data, "errors": ctx.errors, "reason": "not_in_source"}

        if ctx.data.get("artifact") == "questions":
            self._save_generation(s["user_id"], s["session_id"], ctx.data)

        return {"data": ctx.data, "errors": ctx.errors, "reason": None}

    def _save_generation(self, user_id: UUID, session_id: str, data: dict) -> None:
        """Persist the running set so the next "more" avoids everything shown.

        Accumulates rather than replaces: after three continuations the fourth
        must avoid all fifteen prior questions, not just the last five.
        """
        prior = self._scratch.get(user_id, session_id, "last_questions") or []
        texts = prior + [q["question"] for q in data.get("questions", [])]
        if texts:
            self._scratch.set(user_id, session_id, "last_questions", texts)
        if data.get("chunks"):
            self._scratch.set(user_id, session_id, "last_chunks", data["chunks"])


    def _respond(self, s: GraphState) -> GraphState:
        """Build the chat-column line.

        Always produced, even for a generation — the conversation stays
        continuous while structured output accumulates in the side panel.
        """
        if s.get("reason"):
            return {"reply": ""}

        d = s.get("data", {})
        artifact = d.get("artifact")

        if artifact == "questions":
            n = len(d.get("questions", []))
            return {"reply": f"Generated {n} question{'s' if n != 1 else ''}. "
                             f"They're in the practice panel."}
        if d.get("answer"):
            return {"reply": d["answer"]}
        if s.get("errors"):
            return {"reply": "Something went wrong. Please try again."}
        return {"reply": "Done."}


    def run(self, message: str,
            user_id: UUID, session_id: str = "default",
            doc_ids: list[str] | None = None) -> dict:
    
        final = self._graph.invoke({
            "session_id": session_id,
            "user_id": user_id,
            "message": message,
            "doc_ids": doc_ids or [],
            "data": {},
        })
        return {
            "session_id": session_id,
            "user_id": user_id,
            "intent": final.get("intent", ""),
            "reply": final.get("reply", ""),
            "data": final.get("data", {}),
            "errors": final.get("errors", []),
            "reason": final.get("reason"),
        }
