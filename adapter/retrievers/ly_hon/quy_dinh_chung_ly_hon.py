"""Back-compat shim — moved to server.agents.retrievers.ly_hon.quy_dinh_chung_ly_hon (Phase 3)."""
from server.agents.retrievers.ly_hon.quy_dinh_chung_ly_hon import *  # noqa: F401,F403


import warnings as _warnings

_warnings.warn(
    f"{__name__} là shim back-compat (refactor sang cây server/); "
    "hãy import từ vị trí server.* mới. Shim sẽ bị gỡ ở PR sau.",
    DeprecationWarning,
    stacklevel=2,
)
