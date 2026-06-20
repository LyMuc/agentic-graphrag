"""Conversation history budgeting and deterministic retrieval-memory support."""
from __future__ import annotations

import os
import re
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, Iterable

from application.legal_context import (
    decode_legal_context_bundle,
    process_context_strings,
)
from application.vi_phrase_match import prepare_question
from utils.utils import chuan_hoa_thoi_diem_su_kien


RECENT_FULL_TURNS = int(os.environ.get("RECENT_FULL_TURNS", "4"))
ROUTER_HISTORY_MAX_TOKENS = int(
    os.environ.get("ROUTER_HISTORY_MAX_TOKENS", "3000")
)
RESPONSE_HISTORY_MAX_TOKENS = int(
    os.environ.get("RESPONSE_HISTORY_MAX_TOKENS", "4000")
)
OLDER_TURN_INDEX_LIMIT = int(os.environ.get("OLDER_TURN_INDEX_LIMIT", "20"))
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


def estimate_tokens(text: str) -> int:
    """Estimate token usage locally without an API or model tokenizer.

    Args:
        text: Arbitrary message or anchor text.

    Returns:
        Conservative positive token estimate based on Unicode word/punctuation
        groups and character length. Empty text returns zero.
    """

    if not text:
        return 0
    pieces = re.findall(r"\w+|[^\w\s]", text, flags=re.UNICODE)
    return max(len(pieces), (len(text) + 3) // 4)


def estimate_messages_tokens(messages: Iterable[dict[str, str]]) -> int:
    """Estimate total tokens for OpenAI-style chat messages.

    Args:
        messages: Iterable of dictionaries with ``role`` and ``content``.

    Returns:
        Estimated tokens including a small per-message framing overhead.
    """

    return sum(estimate_tokens(str(message.get("content") or "")) + 4 for message in messages)


def _history_turns(history: list[dict[str, str]]) -> list[list[dict[str, str]]]:
    """Group linear user/assistant history into conversational turns.

    Args:
        history: Full OpenAI-style message history.

    Returns:
        Ordered turns. A user message starts a new turn; following assistant
        messages remain in that turn. Leading assistant messages form a
        standalone turn and are preserved.
    """

    turns: list[list[dict[str, str]]] = []
    for message in history:
        normalized = {
            "role": str(message.get("role") or ""),
            "content": str(message.get("content") or ""),
        }
        if normalized["role"] == "user" or not turns:
            turns.append([normalized])
        else:
            turns[-1].append(normalized)
    return turns


def _fit_recent_turns(
    turns: list[list[dict[str, str]]],
    max_tokens: int,
) -> tuple[list[dict[str, str]], int]:
    """Fit newest complete turns inside a token budget.

    Args:
        turns: Candidate turns ordered oldest to newest.
        max_tokens: Maximum estimated token budget.

    Returns:
        Tuple of flattened messages in chronological order and tokens used.
        If the newest turn alone exceeds the budget, its user message is kept
        when possible so the immediate conversational reference is not lost.
    """

    selected: list[list[dict[str, str]]] = []
    used = 0
    for turn in reversed(turns):
        turn_tokens = estimate_messages_tokens(turn)
        if used + turn_tokens <= max_tokens:
            selected.append(turn)
            used += turn_tokens
            continue
        if not selected:
            user_messages = [m for m in turn if m.get("role") == "user"]
            if user_messages:
                user_message = user_messages[-1]
                user_tokens = estimate_messages_tokens([user_message])
                if user_tokens <= max_tokens:
                    selected.append([user_message])
                    used += user_tokens
        break
    selected.reverse()
    return [message for turn in selected for message in turn], used


def _anchor_text(anchor: dict[str, Any]) -> str:
    """Render one compact old-turn anchor for Router/LLM context.

    Args:
        anchor: Turn metadata containing IDs, resolved queries, retrievers, and
            context references.

    Returns:
        One compact single-line anchor.
    """

    queries = " | ".join(str(q) for q in anchor.get("resolved_queries") or [] if q)
    retrievers = ",".join(
        str(name) for name in anchor.get("retriever_names") or [] if name
    )
    refs = ",".join(str(ref) for ref in anchor.get("context_refs") or [] if ref)
    return (
        f"{anchor.get('turn_id', '')} | resolved_query={queries} | "
        f"retrievers={retrievers} | context_refs={refs}"
    )


def _anchor_relevance(anchor: dict[str, Any], current_query: str, index: int) -> tuple[int, int]:
    """Score an anchor by lexical relevance and recency.

    Args:
        anchor: Old-turn anchor to rank.
        current_query: Current raw user message.
        index: Anchor position in chronological order.

    Returns:
        Sort tuple where larger overlap and newer index rank first.
    """

    query_terms = set(prepare_question(current_query).split())
    anchor_terms = set(prepare_question(_anchor_text(anchor)).split())
    return len(query_terms & anchor_terms), index


def build_working_history(
    full_history: list[dict[str, str]],
    anchors: list[dict[str, Any]],
    *,
    current_query: str,
    recent_full_turns: int = RECENT_FULL_TURNS,
    max_tokens: int = ROUTER_HISTORY_MAX_TOKENS,
    older_turn_index_limit: int = OLDER_TURN_INDEX_LIMIT,
) -> list[dict[str, str]]:
    """Build bounded history from recent full turns plus compact old anchors.

    Args:
        full_history: Complete user/assistant history retained for UI and audit.
        anchors: Compact metadata for prior routed turns.
        current_query: Current raw user message used to rank older anchors.
        recent_full_turns: Number of newest turns considered in full form.
        max_tokens: Local estimated token budget for the returned messages.
        older_turn_index_limit: Maximum old anchors considered for inclusion.

    Returns:
        OpenAI-style messages within the budget. A system message containing
        selected old anchors precedes recent full messages when space permits.
    """

    if max_tokens <= 0:
        return []
    turns = _history_turns(full_history)
    recent_candidates = turns[-max(0, recent_full_turns) :] if recent_full_turns else []
    recent_messages, used = _fit_recent_turns(recent_candidates, max_tokens)

    older_anchors = (
        anchors[: -max(0, recent_full_turns)]
        if recent_full_turns and len(anchors) > recent_full_turns
        else ([] if recent_full_turns else anchors)
    )
    indexed = list(enumerate(older_anchors[-max(0, older_turn_index_limit) :]))
    indexed.sort(
        key=lambda pair: _anchor_relevance(pair[1], current_query, pair[0]),
        reverse=True,
    )

    selected_lines: list[str] = []
    anchor_budget = max_tokens - used
    header = (
        "CHỈ MỤC CÁC LƯỢT HỘI THOẠI CŨ. Dùng để giải tham chiếu; "
        "không xem đây là căn cứ pháp lý:\n"
    )
    header_tokens = estimate_tokens(header) + 4
    if anchor_budget > header_tokens:
        anchor_used = header_tokens
        for _, anchor in indexed:
            line = _anchor_text(anchor)
            line_tokens = estimate_tokens(line) + 1
            if anchor_used + line_tokens > anchor_budget:
                continue
            selected_lines.append(line)
            anchor_used += line_tokens

    anchor_message = (
        [{"role": "system", "content": header + "\n".join(selected_lines)}]
        if selected_lines
        else []
    )
    return [*anchor_message, *recent_messages]


def context_refs_from_messages(messages: Iterable[dict[str, str]]) -> list[str]:
    """Extract context references mentioned in compact anchor messages.

    Args:
        messages: Working-history messages that may contain
            ``context_refs=ref1,ref2`` anchor fields.

    Returns:
        Unique context references in first-seen order.
    """

    refs: list[str] = []
    pattern = re.compile(r"context_refs=([^\n|]*)")
    for message in messages:
        content = str(message.get("content") or "")
        for match in pattern.finditer(content):
            for ref in match.group(1).split(","):
                value = ref.strip()
                if value and value not in refs:
                    refs.append(value)
    return refs


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
