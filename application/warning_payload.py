"""Back-compat shim — moved to ``server.domain.legal.warnings`` (Phase 1 refactor)."""
from __future__ import annotations

from server.domain.legal.warnings import (
    build_conflict_warning_payload,
    build_legal_warning_metadata,
    build_validity_warning_payload,
    dedupe_rows_by_ancestor,
    format_provision_label,
)

__all__ = [
    "build_conflict_warning_payload",
    "build_legal_warning_metadata",
    "build_validity_warning_payload",
    "dedupe_rows_by_ancestor",
    "format_provision_label",
]
