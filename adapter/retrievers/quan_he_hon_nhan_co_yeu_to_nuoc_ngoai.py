"""Back-compat shim — moved to server.agents.retrievers.quan_he_hon_nhan_co_yeu_to_nuoc_ngoai (Phase 3)."""
from server.agents.retrievers.quan_he_hon_nhan_co_yeu_to_nuoc_ngoai import *  # noqa: F401,F403


import warnings as _warnings

_warnings.warn(
    f"{__name__} là shim back-compat (refactor sang cây server/); "
    "hãy import từ vị trí server.* mới. Shim sẽ bị gỡ ở PR sau.",
    DeprecationWarning,
    stacklevel=2,
)
