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
