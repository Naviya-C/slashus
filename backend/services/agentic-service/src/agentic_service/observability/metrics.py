"""Prometheus metrics."""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

TOOL_CALLS = Counter("agentic_tool_calls_total", "Tool invocations", ["tool", "outcome"])
TOOL_LATENCY = Histogram(
    "agentic_tool_latency_seconds",
    "Per-tool latency",
    ["tool"],
    buckets=(0.05, 0.1, 0.5, 1, 2, 5, 10, 30),
)
# The defining metric of a real agent loop: how many tool calls the MODEL chose
# to make. In a hardcoded pipeline this is a constant; here it is a distribution.
LOOP_ITERATIONS = Histogram(
    "agentic_loop_iterations", "Model calls per turn", buckets=(1, 2, 3, 4, 5, 6, 8, 12, 20)
)
TURN_DURATION = Histogram(
    "agentic_turn_seconds",
    "End-to-end turn latency",
    buckets=(0.5, 1, 2, 5, 10, 20, 40, 60, 120),
)
TURN_OUTCOMES = Counter("agentic_turn_outcomes_total", "Turn outcomes", ["outcome"])
LLM_TOKENS = Counter("agentic_llm_tokens_total", "Tokens consumed", ["kind"])
LLM_CALLS = Counter("agentic_llm_calls_total", "Model calls", ["outcome"])
MEMORY_RECALL = Histogram(
    "agentic_memory_recall_seconds",
    "Time to recall all memory types",
    buckets=(0.005, 0.01, 0.05, 0.1, 0.25, 0.5, 1, 2),
)
MEMORY_WRITES = Counter("agentic_memory_writes_total", "Memories written", ["kind", "path"])
WINDOW_TOKENS = Histogram(
    "agentic_window_messages",
    "Messages sent to the model after trimming",
    buckets=(1, 5, 10, 20, 40, 80, 160),
)
CONSOLIDATIONS = Counter("agentic_consolidations_total", "Background consolidations", ["outcome"])
VECTOR_ERRORS = Counter("agentic_vector_errors_total", "gRPC failures", ["code"])
COMPONENT_UP = Gauge("agentic_component_up", "1 when a dependency is healthy", ["component"])

# -- semantic response cache ------------------------------------------------

CACHE_EVENTS = Counter(
    "agentic_cache_events_total",
    "Semantic cache outcomes. `skip` with reason=greeting is expected and "
    "healthy: greetings are answered live by design.",
    ["event", "reason"],
)
CACHE_LOOKUP = Histogram(
    "agentic_cache_lookup_seconds",
    "Cache lookup latency including embedding",
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5),
)
