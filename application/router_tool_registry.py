"""Back-compat shim — moved to ``server.interface.router_tools`` (Phase 4)."""
from server.interface.router_tools import *  # noqa: F401,F403
from server.interface.router_tools import (  # noqa: F401
    router_tool_registry,
    router_tools_for_llm,
)


import warnings as _warnings

_warnings.warn(
    f"{__name__} là shim back-compat (refactor sang cây server/); "
    "hãy import từ vị trí server.* mới. Shim sẽ bị gỡ ở PR sau.",
    DeprecationWarning,
    stacklevel=2,
)
