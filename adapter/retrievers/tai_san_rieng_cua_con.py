"""Back-compat shim — moved to server.agents.retrievers.tai_san_rieng_cua_con (Phase 3)."""
from server.agents.retrievers.tai_san_rieng_cua_con import *  # noqa: F401,F403


import warnings as _warnings

_warnings.warn(
    f"{__name__} là shim back-compat (refactor sang cây server/); "
    "hãy import từ vị trí server.* mới. Shim sẽ bị gỡ ở PR sau.",
    DeprecationWarning,
    stacklevel=2,
)
