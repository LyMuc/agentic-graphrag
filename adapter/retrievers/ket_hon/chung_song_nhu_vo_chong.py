"""Back-compat shim — moved to server.agents.retrievers.ket_hon.chung_song_nhu_vo_chong (Phase 3)."""
from server.agents.retrievers.ket_hon.chung_song_nhu_vo_chong import *  # noqa: F401,F403


import warnings as _warnings

_warnings.warn(
    f"{__name__} là shim back-compat (refactor sang cây server/); "
    "hãy import từ vị trí server.* mới. Shim sẽ bị gỡ ở PR sau.",
    DeprecationWarning,
    stacklevel=2,
)
