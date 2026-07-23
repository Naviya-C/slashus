"""Streamlit frontend — test UI over the FastAPI backend.

Run the API first:   uvicorn src.api.server:api --reload --port 8080
Then:                streamlit run frontend/app.py

Identity: the sidebar takes a user id (UUID) and a session id. The user id is
sent as the X-User-Id header on every request — the same header the API
gateway will inject once auth exists. Entering a user id and pressing "Load"
pulls that user's past turns from the backend and renders them.

This is a thin client: it POSTs to /chat and renders whatever artifact the
orchestrator returns. No agent logic lives here.
"""

from __future__ import annotations

import os
import uuid

import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8080")
REQUEST_TIMEOUT = 180

st.set_page_config(page_title="Agentic Study Assistant", page_icon="📚", layout="centered")


# --------------------------------------------------------------------------
# state
# --------------------------------------------------------------------------

def _init_state() -> None:
    if "user_id" not in st.session_state:
        st.session_state.user_id = str(uuid.uuid4())
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    if "history" not in st.session_state:
        st.session_state.history = []
    if "status" not in st.session_state:
        st.session_state.status = ""


_init_state()


def is_uuid(value: str) -> bool:
    try:
        uuid.UUID(value.strip())
        return True
    except (ValueError, AttributeError):
        return False


def headers() -> dict:
    """Identity header. The gateway will supply this from a verified token
    later; for local testing the sidebar supplies it."""
    return {"X-User-Id": st.session_state.user_id}


# --------------------------------------------------------------------------
# backend calls
# --------------------------------------------------------------------------

def load_history() -> None:
    """Fetch this user+session's past turns and put them in local history."""
    try:
        resp = requests.get(
            f"{API_URL}/history",
            params={"session_id": st.session_state.session_id, "limit": 50},
            headers=headers(),
            timeout=30,
        )
        resp.raise_for_status()
        turns = resp.json().get("turns", [])
    except requests.HTTPError as e:
        code = e.response.status_code if e.response is not None else "?"
        st.session_state.status = f"Could not load history (HTTP {code})."
        return
    except Exception as e:
        st.session_state.status = f"Could not load history: {e}"
        return

    st.session_state.history = [
        {
            "message": t.get("user_message", ""),
            "reply": t.get("assistant_message", ""),
            "intent": t.get("intent", ""),
            # Past turns store the reply text, not the full artifact payload.
            "data": t.get("data") or {},
        }
        for t in turns
    ]
    st.session_state.status = f"Loaded {len(turns)} past turn(s)."


def send_message(prompt: str) -> dict | None:
    try:
        resp = requests.post(
            f"{API_URL}/chat",
            json={"message": prompt, "session_id": st.session_state.session_id},
            headers=headers(),
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.HTTPError as e:
        detail = ""
        try:
            detail = e.response.json().get("detail", "")
        except Exception:
            pass
        st.error(f"Backend error {e.response.status_code}: {detail or e}")
    except Exception as e:
        st.error(f"Backend error: {e}")
    return None


# --------------------------------------------------------------------------
# sidebar — identity
# --------------------------------------------------------------------------

with st.sidebar:
    st.subheader("Identity")

    user_input = st.text_input(
        "User ID (UUID)",
        value=st.session_state.user_id,
        key="user_input",
        help="Sent as the X-User-Id header. All data is scoped to this id.",
    )
    session_input = st.text_input(
        "Session ID",
        value=st.session_state.session_id,
        key="session_input",
        help="One conversation thread for this user.",
    )

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("Load", use_container_width=True):
            if not is_uuid(user_input):
                st.session_state.status = "User ID must be a valid UUID."
            else:
                st.session_state.user_id = user_input.strip()
                st.session_state.session_id = session_input.strip()
                load_history()
                st.rerun()
    with col_b:
        if st.button("New user", use_container_width=True):
            st.session_state.user_id = str(uuid.uuid4())
            st.session_state.session_id = str(uuid.uuid4())
            st.session_state.history = []
            st.session_state.status = "Started a new user."
            st.rerun()

    if st.button("New session (same user)", use_container_width=True):
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.history = []
        st.session_state.status = "Started a new session."
        st.rerun()

    if st.session_state.status:
        st.caption(st.session_state.status)

    st.markdown("---")
    st.caption("Active")
    st.code(f"user   : {st.session_state.user_id}\nsession: {st.session_state.session_id}")

    st.markdown("---")
    st.subheader("Try")
    st.markdown(
        "- දීපාවලී උත්සවය ගැන ප්‍රශ්න 5ක් දෙන්න\n"
        "- තවත් ප්‍රශ්න දෙන්න\n"
        "- 5 MCQ with answers about photosynthesis\n"
        "- summarize the Deepavali lesson\n"
        "- make 4 flashcards about the water cycle"
    )


# --------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------

def render_data(data: dict) -> None:
    if not data:
        return
    artifact = data.get("artifact")

    if artifact == "questions":
        for i, q in enumerate(data.get("questions", []), 1):
            st.markdown(f"**{i}. [{q.get('type','')}]** {q.get('question','')}")
            for o in q.get("options", []):
                st.markdown(
                    f"&nbsp;&nbsp;&nbsp;{o.get('label','')}) {o.get('text','')}",
                    unsafe_allow_html=True,
                )
            if q.get("answer"):
                st.success(f"Answer: {q['answer']}")
            if q.get("source_pages"):
                st.caption(f"pages: {q['source_pages']}")

    elif artifact == "summary":
        st.markdown(data.get("summary", ""))

    elif artifact == "flashcards":
        for c in data.get("flashcards", []):
            with st.expander(c.get("front", "")):
                st.write(c.get("back", ""))

    elif artifact == "explanation":
        st.markdown(data.get("explanation", ""))

    elif data.get("marking"):
        m = data["marking"]
        st.metric("Score", f"{m['total_score']:.1f} / {m['total_max']:.1f}")
        for g in m.get("graded", []):
            with st.expander(f"{g['question'][:60]} — {g['score']}/{g['max_score']}"):
                st.write(g.get("feedback", ""))
                if g.get("suggestions"):
                    st.info("Suggestions: " + "; ".join(g["suggestions"]))
        if m.get("weak_topics"):
            st.warning("Weak topics: " + ", ".join(m["weak_topics"]))

    elif data.get("chunks"):
        for c in data["chunks"][:8]:
            title = c.get("title", "")
            st.markdown(f"**p{c.get('page','?')} · {title}**")
            st.caption(c.get("content", "")[:400])


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

st.title("📚 Agentic Study Assistant")
st.caption("Ask for lesson content, questions, summaries, flashcards, or explanations.")

if not st.session_state.history:
    st.info("No messages in this session yet. Ask something below, or load a "
            "past session from the sidebar.")

for turn in st.session_state.history:
    with st.chat_message("user"):
        st.write(turn["message"])
    with st.chat_message("assistant"):
        if turn.get("intent"):
            st.caption(turn["intent"])
        st.write(turn["reply"])
        render_data(turn.get("data", {}))

prompt = st.chat_input("Ask something…")
if prompt:
    with st.chat_message("user"):
        st.write(prompt)
    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            result = send_message(prompt)
        if result:
            st.caption(result.get("intent", ""))
            st.write(result.get("reply", ""))
            render_data(result.get("data", {}))
            st.session_state.history.append({
                "message": prompt,
                "reply": result.get("reply", ""),
                "intent": result.get("intent", ""),
                "data": result.get("data", {}),
            })
            if result.get("errors"):
                st.warning("; ".join(result["errors"]))