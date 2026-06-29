"""Back-compat shim — moved to ``server.domain.legal.codec`` (Phase 1 refactor).

22 retriever vẫn import ``encode_context_record`` từ đây cho tới khi chuyển sang
``server.agents.retrievers`` ở Phase 3.
"""
from __future__ import annotations

from server.domain.legal.codec import (
    LEGAL_CONTEXT_PREFIX,
    LEGAL_CONTEXT_SCHEMA_VERSION,
    _as_dict_list,
    _unique_dicts,
    build_legal_context_bundle,
    decode_legal_context_bundle,
    encode_context_record,
    encode_legal_context_bundle,
)

__all__ = [
    "LEGAL_CONTEXT_PREFIX",
    "LEGAL_CONTEXT_SCHEMA_VERSION",
    "build_legal_context_bundle",
    "decode_legal_context_bundle",
    "encode_context_record",
    "encode_legal_context_bundle",
]


import warnings as _warnings

_warnings.warn(
    f"{__name__} là shim back-compat (refactor sang cây server/); "
    "hãy import từ vị trí server.* mới. Shim sẽ bị gỡ ở PR sau.",
    DeprecationWarning,
    stacklevel=2,
)
