"""Back-compat shim — moved to ``server.agents.router.tool_factory`` (Phase 4)."""
from server.agents.router.tool_factory import *  # noqa: F401,F403
from server.agents.router.tool_factory import build_presentation_tools  # noqa: F401


import warnings as _warnings

_warnings.warn(
    f"{__name__} là shim back-compat (refactor sang cây server/); "
    "hãy import từ vị trí server.* mới. Shim sẽ bị gỡ ở PR sau.",
    DeprecationWarning,
    stacklevel=2,
)
