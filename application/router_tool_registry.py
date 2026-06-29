"""Back-compat shim — moved to ``server.interface.router_tools`` (Phase 4)."""
from server.interface.router_tools import *  # noqa: F401,F403
from server.interface.router_tools import (  # noqa: F401
    router_tool_registry,
    router_tools_for_llm,
)
