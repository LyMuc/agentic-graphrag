"""Back-compat shim — moved to ``server.domain.legal.bundle`` (Phase 1 refactor).

Importers tiếp tục dùng ``application.legal_context`` cho tới khi cập nhật sang
đường dẫn mới. Re-export đầy đủ API mà các call site đang dùng (gồm cả các symbol
bắt nguồn từ codec).
"""
from __future__ import annotations

from server.domain.legal.bundle import (
    ContextPipelineResult,
    LEGAL_CONTEXT_SCHEMA_VERSION,
    build_legal_context_bundle,
    decode_legal_context_bundle,
    encode_context_record,
    encode_legal_context_bundle,
    legal_context_bundle_to_context_tho,
    merge_legal_context_bundles,
    process_context_strings,
    render_legal_context_bundle,
)

__all__ = [
    "ContextPipelineResult",
    "LEGAL_CONTEXT_SCHEMA_VERSION",
    "build_legal_context_bundle",
    "decode_legal_context_bundle",
    "encode_context_record",
    "encode_legal_context_bundle",
    "legal_context_bundle_to_context_tho",
    "merge_legal_context_bundles",
    "process_context_strings",
    "render_legal_context_bundle",
]
