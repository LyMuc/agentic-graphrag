"""Gắn RetrieverPolicy với tool_calls thô từ Router LLM (benchmark/test, không dùng production)."""

from __future__ import annotations

from typing import Any

from application.retriever_catalog import DIRECT_TOOLS

from retriever_policy.models import PolicyCandidate, PolicyDecision
from retriever_policy.policy import coerce_confidence_score, evaluate_retriever_policy

EXCLUSIVE_DIRECT_TOOLS = frozenset({"clarify", "respond"})


def _tool_call_name(tool_call: dict[str, Any]) -> str:
    return str(tool_call.get("name", ""))


def unique_tool_calls(tool_calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen_tools: set[str] = set()
    unique: list[dict[str, Any]] = []
    for tool_call in tool_calls:
        tool_name = _tool_call_name(tool_call)
        if not tool_name or tool_name in seen_tools:
            continue
        seen_tools.add(tool_name)
        unique.append(tool_call)
    return unique


def _resolved_query(tool_call: dict[str, Any], fallback_question: str) -> str:
    args = tool_call.get("args") or {}
    query = str(args.get("query") or "").strip()
    return query or fallback_question


def policy_candidates_from_tool_calls(
    tool_calls: list[dict[str, Any]],
) -> list[PolicyCandidate]:
    candidates: list[PolicyCandidate] = []
    for call in unique_tool_calls(tool_calls):
        name = _tool_call_name(call)
        if not name:
            continue
        args = call.get("args", {})
        confidence = None
        if isinstance(args, dict):
            confidence = coerce_confidence_score(args.get("confidence_score"))
        candidates.append(PolicyCandidate(name=name, confidence_score=confidence))
    return candidates


def build_policy_tool_calls(
    llm_tool_calls: list[dict[str, Any]],
    final_tools: list[str],
) -> list[dict[str, Any]]:
    by_name: dict[str, dict[str, Any]] = {}
    for call in unique_tool_calls(llm_tool_calls):
        name = _tool_call_name(call)
        by_name[name] = {**call, "name": name}

    out: list[dict[str, Any]] = []
    for tool_name in final_tools:
        out.append(by_name.get(tool_name, {"name": tool_name, "args": {}}))
    return out


def evaluate_tool_calls_policy(
    question: str,
    llm_tool_calls: list[dict[str, Any]],
) -> PolicyDecision:
    """Apply RetrieverPolicy independently to each resolved tool query."""
    unique_calls = unique_tool_calls(llm_tool_calls)
    candidates = [_tool_call_name(call) for call in unique_calls]
    confidence_candidates = policy_candidates_from_tool_calls(unique_calls)
    candidate_confidences = {
        candidate.name: candidate.confidence_score
        for candidate in confidence_candidates
        if candidate.confidence_score is not None
    }
    exclusive_call = next(
        (
            call
            for call in unique_calls
            if _tool_call_name(call) in EXCLUSIVE_DIRECT_TOOLS
        ),
        None,
    )
    if exclusive_call is not None:
        exclusive_name = _tool_call_name(exclusive_call)
        rejected_tools = {
            name: f"{exclusive_name} is an exclusive direct-response tool."
            for name in candidates
            if name != exclusive_name
        }
        return PolicyDecision(
            question=question,
            prepared_question="",
            llm_candidates=candidates,
            final_tools=[exclusive_name],
            rejected_tools=rejected_tools,
            audit=[
                "LLM candidates: "
                + (", ".join(candidates) if candidates else "(none)"),
                f"Final retrievers: {exclusive_name}",
                (
                    f"{exclusive_name}: kept exclusively; retrievers and other "
                    "direct tools were skipped."
                ),
            ],
            candidate_confidences=candidate_confidences,
        )

    final_tools: list[str] = []
    rejected_tools: dict[str, str] = {}
    audit = [
        "LLM candidates: " + (", ".join(candidates) if candidates else "(none)")
    ]
    prepared_parts: list[str] = []
    for call in unique_calls:
        name = _tool_call_name(call)
        resolved = _resolved_query(call, question)
        if name in DIRECT_TOOLS:
            final_tools.append(name)
            audit.append(f"{name}: direct tool kept.")
            continue
        args = call.get("args") or {}
        confidence = (
            coerce_confidence_score(args.get("confidence_score"))
            if isinstance(args, dict)
            else None
        )
        decision = evaluate_retriever_policy(
            resolved,
            [PolicyCandidate(name=name, confidence_score=confidence)],
        )
        prepared_parts.append(decision.prepared_question)
        if name in decision.final_tools:
            final_tools.append(name)
            audit.append(f"{name}: kept for resolved query '{resolved}'.")
            if decision.fallback_reason:
                audit.append(f"{name}: fallback kept - {decision.fallback_reason}")
        else:
            reason = decision.rejected_tools.get(name, "RetrieverPolicy rejected.")
            rejected_tools[name] = reason
            audit.append(f"{name}: rejected for resolved query '{resolved}' ({reason})")
    audit.insert(
        1,
        "Final retrievers: " + (", ".join(final_tools) if final_tools else "(none)"),
    )
    return PolicyDecision(
        question=question,
        prepared_question=" | ".join(prepared_parts),
        llm_candidates=candidates,
        final_tools=final_tools,
        rejected_tools=rejected_tools,
        audit=audit,
        candidate_confidences=candidate_confidences,
    )


# Alias tương thích test cũ import `_evaluate_tool_calls_policy`.
_evaluate_tool_calls_policy = evaluate_tool_calls_policy
