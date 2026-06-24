# UI/app.py

import streamlit as st
import requests

API_URL = "http://localhost:8090/chat"

st.set_page_config(
    page_title="PDF RAG",
    page_icon="📚",
    layout="wide",
)

st.title("📚 PDF Question Answering")
st.caption("Ask questions about your ingested PDFs.")

# Keep chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display previous messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
question = st.chat_input(
    "Ask a question about your document..."
)

if question:
    # Display user message
    st.session_state.messages.append(
        {
            "role": "user",
            "content": question,
        }
    )

    with st.chat_message("user"):
        st.markdown(question)

    # Call backend
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                response = requests.post(
                    API_URL,
                    json={
                        "question": question
                    },
                    timeout=120,
                )

                response.raise_for_status()

                data = response.json()

                answer = data.get(
                    "answer",
                    "No answer returned."
                )

                sources = data.get(
                    "sources",
                    []
                )

                st.markdown(answer)

                # Store assistant answer
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": answer,
                    }
                )

                # Show retrieved chunks
                if sources:
                    st.divider()
                    st.subheader("Retrieved Chunks")

                    for i, source in enumerate(
                        sources,
                        start=1
                    ):
                        page = source.get(
                            "page_number",
                            "Unknown"
                        )

                        file_name = source.get(
                            "source_file",
                            "Unknown"
                        )

                        text = source.get(
                            "text",
                            ""
                        )

                        with st.expander(
                            f"Source {i} • Page {page}"
                        ):
                            st.caption(
                                f"File: {file_name}"
                            )
                            st.write(text)

            except requests.exceptions.ConnectionError:
                st.error(
                    "Cannot connect to the FastAPI backend. "
                    "Is it running on port 8090?"
                )

            except requests.exceptions.Timeout:
                st.error(
                    "Request timed out."
                )

            except requests.exceptions.HTTPError as e:
                st.error(
                    f"Backend error: {e}"
                )

            except Exception as e:
                st.error(
                    f"Unexpected error: {e}"
                )