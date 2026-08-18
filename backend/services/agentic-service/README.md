# Slashus Agentic Service: Archtecture, Data Flow, and Implementaion Guid

The service is a real model-controlled ReAct agent. It is not a fixed Python router disguised as an agent. langchain.agents.create_agent binds native tools to the LLM, and the LLM decides whether to answer, call a tool, repeat retrieval with new arguments, write memory, create a quiz, or stop.

The architecture:
  - FastAPI provides the HTTP boundary.
  - LangChain/LangGraph provides the agent loop and checkpointed conversation state.
  - Qwen is accessed through an OpenAI-compatible API.
  - PostgreSQL stores sessions, visible chat history, quizzes, answers, and long-term memories.
  - pgvector recalls semantic and episodic memories.
  - Redis stores LangGraph checkpoints and the semantic response cache.
  - The embedding service owns BGE-M3 and Qdrant access behind gRPC.
  - Python not the LLM controls identity, tenancy, limits, persistence, and citation validation.


## System boundary
Client["React client"] --> Gateway["API Gateway"]
Gateway --> API["FastAPI agentic service"]
API --> Runner["TurnRunner"]
Runner --> Cache["Redis semantic cache"]
Runner --> Agent["LangGraph ReAct agent"]
Agent --> LLM["Qwen via Dashscope"]
Agent --> Tools["Native agent tools"]
Tools --> GRPC["gRPC embedding service"]
GRPC --> Qdrant["Qdrant + BGE-M3"]
Tools --> Postgres["PostgreSQL + pgvector"]
Agent --> Checkpoint["Redis checkpointer"]
API --> Postgres

