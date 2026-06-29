"""Bộ nhớ retrieval xác định (deterministic) + tái sử dụng context có kiểm chứng.

Tách từ ``application/conversation_context.py`` trong Phase 4 refactor. Chứa
ReuseValidation, validate_reuse_request, tạo/khôi phục cache entry, anchor lượt,
phiên bản KG cho việc vô hiệu hoá cache.
"""
from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, Iterable

from server.domain.legal.bundle import (
    decode_legal_context_bundle,
    process_context_strings,
)
from server.shared.datetime_vn import chuan_hoa_thoi_diem_su_kien
from server.conversation.history import OLDER_TURN_INDEX_LIMIT

_PROCESS_KG_VERSION = os.environ.get("KG_VERSION") or f"process:{uuid.uuid4().hex}"


@dataclass(frozen=True)
class ReuseValidation:
    """Deterministic validation result for a Router cache-reuse request.

    Attributes:
        allowed: Whether all referenced cache entries are safe to reuse.
        reason: Audit text explaining acceptance or the first rejection.
        contexts: Encoded legal-context strings loaded from accepted entries.
        context_refs: Validated cache reference identifiers.
    """

    allowed: bool
    reason: str
    contexts: list[str]
    context_refs: list[str]


def current_kg_version() -> str:
    """Return the knowledge-graph version used for cache invalidation.

    Returns:
        ``KG_VERSION`` from the environment when configured. Otherwise returns
        a process-unique version so cache entries cannot survive a restart.
    """

    return _PROCESS_KG_VERSION


def retrieval_memory_summary(
    memory: dict[str, dict[str, Any]],
    *,
    preferred_refs: Iterable[str] | None = None,
    max_entries: int = OLDER_TURN_INDEX_LIMIT,
) -> str:
    """Render cache descriptors for the Router without exposing legal content.

    Args:
        memory: Mapping from ``context_ref`` to retrieval-memory entries.
        preferred_refs: References already selected into working-history
            anchors; these are included before recent fallback entries.
        max_entries: Maximum cache descriptors rendered to bound prompt size.

    Returns:
        Compact multiline summary containing reference, retriever, resolved
        query, target dates, and KG version. Returns ``(none)`` when empty.
    """

    if not memory:
        return "(none)"
    selected_refs: list[str] = []
    for ref in preferred_refs or []:
        value = str(ref)
        if value in memory and value not in selected_refs:
            selected_refs.append(value)
    for ref in reversed(list(memory)):
        if ref not in selected_refs:
            selected_refs.append(ref)
        if len(selected_refs) >= max(0, max_entries):
            break
    selected_refs = selected_refs[: max(0, max_entries)]

    lines: list[str] = []
    for ref in selected_refs:
        entry = memory[ref]
        lines.append(
            " | ".join(
                [
                    f"ref={ref}",
                    f"retriever={entry.get('retriever_name', '')}",
                    f"query={entry.get('resolved_query', '')}",
                    f"target_dates={','.join(entry.get('target_dates') or [])}",
                    f"kg_version={entry.get('kg_version', '')}",
                ]
            )
        )
    return "\n".join(lines)


def _expected_target_date(
    tool_args: dict[str, Any],
    today: str,
) -> tuple[str | None, bool | None]:
    """Resolve expected date and date-source flag from Router control args.

    Args:
        tool_args: Router tool arguments containing ``time_scope`` and optional
            ``target_date``.
        today: Current ISO date used for ``current`` scope.

    Returns:
        Tuple ``(target_date, is_user_provided_date)``. Ambiguous or malformed
        explicit dates return ``(None, None)`` and force retrieval.
    """

    time_scope = str(tool_args.get("time_scope") or "current")
    if time_scope == "ambiguous":
        return None, None
    if time_scope == "explicit":
        normalized = chuan_hoa_thoi_diem_su_kien(tool_args.get("target_date"))
        return (normalized, True) if normalized else (None, None)
    return today, False


def validate_reuse_request(
    *,
    tool_name: str,
    tool_args: dict[str, Any],
    memory: dict[str, dict[str, Any]],
    thread_id: str,
    kg_version: str,
    today: str | None = None,
) -> ReuseValidation:
    """Validate a Router request to skip a retriever and reuse cached bundles.

    Args:
        tool_name: Retriever selected by the Router.
        tool_args: Tool arguments including ``context_action``, ``context_refs``,
            ``time_scope``, and optional ``target_date``.
        memory: Current thread's retrieval-memory mapping.
        thread_id: Active Chainlit thread ID.
        kg_version: Current knowledge-graph version.
        today: Optional ISO date override used by deterministic tests.

    Returns:
        ``ReuseValidation`` with accepted encoded contexts or a rejection
        reason. Any uncertainty, malformed bundle, date mismatch, wrong
        retriever/thread, or KG version mismatch rejects reuse.
    """

    if str(tool_args.get("context_action") or "retrieve") != "reuse":
        return ReuseValidation(False, "Router requested retrieval.", [], [])
    refs = [str(ref) for ref in tool_args.get("context_refs") or [] if ref]
    if not refs:
        return ReuseValidation(False, "Reuse requested without context_refs.", [], [])

    expected_date, expected_explicit = _expected_target_date(
        tool_args,
        today or date.today().isoformat(),
    )
    if expected_date is None:
        return ReuseValidation(False, "Time scope is ambiguous.", [], refs)

    contexts: list[str] = []
    for ref in refs:
        entry = memory.get(ref)
        if not entry:
            return ReuseValidation(False, f"Unknown context_ref: {ref}.", [], refs)
        if str(entry.get("thread_id") or "") != str(thread_id):
            return ReuseValidation(False, f"context_ref {ref} belongs to another thread.", [], refs)
        if str(entry.get("retriever_name") or "") != tool_name:
            return ReuseValidation(False, f"context_ref {ref} uses another retriever.", [], refs)
        if str(entry.get("kg_version") or "") != kg_version:
            return ReuseValidation(False, f"context_ref {ref} has stale KG version.", [], refs)

        encoded_contexts = [
            str(value) for value in entry.get("encoded_contexts") or [] if value
        ]
        if not encoded_contexts:
            return ReuseValidation(False, f"context_ref {ref} has no encoded bundle.", [], refs)
        for encoded in encoded_contexts:
            bundle = decode_legal_context_bundle(encoded)
            if bundle is None:
                return ReuseValidation(False, f"context_ref {ref} contains invalid bundle.", [], refs)
            if str(bundle.get("target_date")) != expected_date:
                return ReuseValidation(False, f"context_ref {ref} has another target date.", [], refs)
            if bool(bundle.get("is_user_provided_date")) != expected_explicit:
                return ReuseValidation(False, f"context_ref {ref} has another time scope.", [], refs)
            contexts.append(encoded)

    consolidated = process_context_strings(contexts)
    if not consolidated.encoded_contexts or consolidated.legacy_contexts:
        return ReuseValidation(False, "Cached context could not be consolidated.", [], refs)
    return ReuseValidation(
        True,
        "Reuse accepted by deterministic validation.",
        consolidated.encoded_contexts,
        refs,
    )


def create_retrieval_memory_entries(
    tool_response: list[Any],
    *,
    turn_id: str,
    thread_id: str,
    kg_version: str,
) -> list[dict[str, Any]]:
    """Create persistent cache entries for newly retrieved template contexts.

    Args:
        tool_response: Router execution results for the current turn.
        turn_id: Stable identifier for the current conversational turn.
        thread_id: Active Chainlit thread ID.
        kg_version: Knowledge-graph version associated with the retrieval.

    Returns:
        JSON-safe memory entries. Reused results, direct tools, legacy-only
        contexts, and failed retrievals do not create new cache entries.
    """

    entries: list[dict[str, Any]] = []
    for result in tool_response:
        if not isinstance(result, dict):
            continue
        if result.get("cache_status") == "reused":
            continue
        retriever_name = str(result.get("retriever_name") or "")
        if not retriever_name:
            continue
        pipeline = process_context_strings(result.get("contexts") or [])
        if not pipeline.encoded_contexts:
            continue
        target_dates = [
            str(bundle.get("target_date"))
            for bundle in pipeline.bundles
            if bundle.get("target_date")
        ]
        entries.append(
            {
                "context_ref": uuid.uuid4().hex,
                "turn_id": turn_id,
                "thread_id": str(thread_id),
                "retriever_name": retriever_name,
                "resolved_query": str(result.get("resolved_query") or ""),
                "encoded_contexts": pipeline.encoded_contexts,
                "target_dates": list(dict.fromkeys(target_dates)),
                "kg_version": kg_version,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
    return entries


def build_turn_anchor(
    *,
    turn_id: str,
    tool_response: list[Any],
    new_memory_entries: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Build a compact anchor for one completed routed turn.

    Args:
        turn_id: Stable current-turn identifier.
        tool_response: Results returned by the Router and retrievers.
        new_memory_entries: Cache entries created for newly retrieved contexts.

    Returns:
        JSON-safe anchor containing resolved queries, retriever names, and
        context references, or ``None`` when the turn has no retriever context.
    """

    resolved_queries: list[str] = []
    retriever_names: list[str] = []
    context_refs: list[str] = []
    for result in tool_response:
        if not isinstance(result, dict):
            continue
        query = str(result.get("resolved_query") or "")
        retriever = str(result.get("retriever_name") or "")
        if query and query not in resolved_queries:
            resolved_queries.append(query)
        if retriever and retriever not in retriever_names:
            retriever_names.append(retriever)
        for ref in result.get("context_refs_used") or []:
            value = str(ref)
            if value and value not in context_refs:
                context_refs.append(value)
    for entry in new_memory_entries:
        ref = str(entry.get("context_ref") or "")
        if ref and ref not in context_refs:
            context_refs.append(ref)
    if not retriever_names and not context_refs:
        return None
    return {
        "turn_id": turn_id,
        "resolved_queries": resolved_queries,
        "retriever_names": retriever_names,
        "context_refs": context_refs,
    }


def restore_conversation_state(
    steps: list[dict[str, Any]],
) -> tuple[list[dict[str, str]], dict[str, dict[str, Any]], list[dict[str, Any]]]:
    """Restore full history, retrieval memory, and anchors from Chainlit steps.

    Args:
        steps: Persisted Chainlit thread steps in chronological order.

    Returns:
        Tuple ``(full_history, retrieval_memory, anchors)``. Legacy threads
        lacking the new Router metadata restore messages normally and return
        empty memory/anchor collections.
    """

    full_history: list[dict[str, str]] = []
    memory: dict[str, dict[str, Any]] = {}
    anchors: list[dict[str, Any]] = []
    for step in steps:
        step_type = str(step.get("type") or "")
        if step_type == "user_message":
            full_history.append({"role": "user", "content": str(step.get("output") or "")})
        elif step_type == "assistant_message":
            full_history.append(
                {"role": "assistant", "content": str(step.get("output") or "")}
            )

        metadata = step.get("metadata") or {}
        if not isinstance(metadata, dict):
            continue
        for entry in metadata.get("retrieval_memory_entries") or []:
            if not isinstance(entry, dict):
                continue
            ref = str(entry.get("context_ref") or "")
            if ref:
                memory[ref] = dict(entry)
        anchor = metadata.get("turn_anchor")
        if isinstance(anchor, dict) and anchor.get("turn_id"):
            anchors.append(dict(anchor))
    return full_history, memory, anchors
