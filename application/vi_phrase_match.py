"""Back-compat shim — moved to ``server.shared.phrase_match`` (Phase 1 refactor)."""
from __future__ import annotations

from server.shared.phrase_match import (
    DEFAULT_FUZZY_THRESHOLD,
    MatchMode,
    fold_vi,
    match_phrase,
    match_phrase_group,
    match_phrase_groups,
    prepare_question,
)

__all__ = [
    "DEFAULT_FUZZY_THRESHOLD",
    "MatchMode",
    "fold_vi",
    "match_phrase",
    "match_phrase_group",
    "match_phrase_groups",
    "prepare_question",
]


import warnings as _warnings

_warnings.warn(
    f"{__name__} là shim back-compat (refactor sang cây server/); "
    "hãy import từ vị trí server.* mới. Shim sẽ bị gỡ ở PR sau.",
    DeprecationWarning,
    stacklevel=2,
)
