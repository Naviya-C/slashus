"""Tools: the ONLY things that touch the outside world.

The LLM decides which tool runs and with what arguments. It never holds a
database handle, a gRPC channel, or a user id it did not receive. That
separation is the whole security model: a prompt injection inside a retrieved
Sinhala textbook chunk can at worst cause a differently-argued tool call, and
every tool re-derives ownership from the SESSION rather than from anything the
model produced.

See tools/base.py for why arguments are validated rather than trusted.
"""

from tools.base import Tool, ToolError, ToolRegistry, ToolResult, build_tools

__all__ = ["Tool", "ToolError", "ToolRegistry", "ToolResult", "build_tools"]
