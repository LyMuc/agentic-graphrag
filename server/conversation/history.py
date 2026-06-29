"""Lập ngân sách lịch sử hội thoại (token-bounded working history).

Tách từ ``application/conversation_context.py`` trong Phase 4 refactor. Chứa các
env knob token và logic chọn lượt gần + chỉ mục anchor lượt cũ.
"""
from __future__ import annotations

import os
import re
from typing import Any, Iterable

from server.shared.phrase_match import prepare_question

RECENT_FULL_TURNS = int(os.environ.get("RECENT_FULL_TURNS", "4"))
ROUTER_HISTORY_MAX_TOKENS = int(
    os.environ.get("ROUTER_HISTORY_MAX_TOKENS", "3000")
)
RESPONSE_HISTORY_MAX_TOKENS = int(
    os.environ.get("RESPONSE_HISTORY_MAX_TOKENS", "4000")
)
OLDER_TURN_INDEX_LIMIT = int(os.environ.get("OLDER_TURN_INDEX_LIMIT", "20"))


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
