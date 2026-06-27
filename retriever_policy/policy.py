from __future__ import annotations

from typing import Any

from application.retriever_catalog import (
    DIRECT_TOOLS,
    RetrieverSpec,
    TriggerRule,
    get_retriever_spec,
    prepare_question,
)

from retriever_policy.models import PolicyCandidate, PolicyDecision


def coerce_confidence_score(value: Any) -> float | None:
    if value is None:
        return None
    try:
        score = float(value)
    except (TypeError, ValueError):
        return None
    if score < 0.0:
        return 0.0
    if score > 1.0:
        return 1.0
    return score


def _coerce_candidate(item: str | PolicyCandidate | dict[str, Any]) -> PolicyCandidate | None:
    if isinstance(item, PolicyCandidate):
        name = str(item.name or "").strip()
        if not name:
            return None
        return PolicyCandidate(
            name=name,
            confidence_score=coerce_confidence_score(item.confidence_score),
        )

    if isinstance(item, dict):
        raw_name = item.get("name") or item.get("tool_name")
        name = str(raw_name or "").strip()
        if not name:
            return None
        return PolicyCandidate(
            name=name,
            confidence_score=coerce_confidence_score(item.get("confidence_score")),
        )

    name = str(item or "").strip()
    if not name:
        return None
    return PolicyCandidate(name=name)


def _unique_policy_candidates(
    candidates: list[str | PolicyCandidate | dict[str, Any]],
) -> list[PolicyCandidate]:
    seen: set[str] = set()
    out: list[PolicyCandidate] = []
    for item in candidates:
        candidate = _coerce_candidate(item)
        if candidate is None or candidate.name in seen:
            continue
        seen.add(candidate.name)
        out.append(candidate)
    return out


def _candidate_confidence_map(candidates: list[PolicyCandidate]) -> dict[str, float]:
    return {
        candidate.name: candidate.confidence_score
        for candidate in candidates
        if candidate.confidence_score is not None
    }


def _select_fallback_candidate(candidates: list[PolicyCandidate]) -> PolicyCandidate | None:
    known_retrievers = [
        candidate
        for candidate in candidates
        if candidate.name not in DIRECT_TOOLS and get_retriever_spec(candidate.name) is not None
    ]
    if not known_retrievers:
        return None

    scored = [
        candidate
        for candidate in known_retrievers
        if candidate.confidence_score is not None
    ]
    if not scored:
        return known_retrievers[0]
    return max(scored, key=lambda candidate: candidate.confidence_score or 0.0)


def _matching_rules(
    rules: tuple[TriggerRule, ...],
    prepared_question: str,
) -> list[TriggerRule]:
    return [rule for rule in rules if rule.matches(prepared_question)]


def retriever_is_justified(
    spec: RetrieverSpec,
    prepared_question: str,
) -> tuple[bool, str]:
    required_hits = _matching_rules(spec.required_triggers, prepared_question)
    if required_hits:
        return True, required_hits[0].reason

    support_hits = _matching_rules(spec.support_triggers, prepared_question)
    if support_hits:
        return True, support_hits[0].reason

    return False, "No required/support trigger match."


def filter_retriever_candidates(
    question: str,
    llm_candidate_tools: list[str | PolicyCandidate | dict[str, Any]],
) -> PolicyDecision:
    prepared_question = prepare_question(question)
    policy_candidates = _unique_policy_candidates(llm_candidate_tools)
    llm_candidates = [candidate.name for candidate in policy_candidates]
    candidate_confidences = _candidate_confidence_map(policy_candidates)

    final_tools: list[str] = []
    rejected_tools: dict[str, str] = {}

    for name in llm_candidates:
        if name in DIRECT_TOOLS:
            final_tools.append(name)
            continue

        spec = get_retriever_spec(name)
        if spec is None:
            rejected_tools[name] = "Unknown retriever name."
            continue

        justified, reason = retriever_is_justified(spec, prepared_question)
        if justified:
            final_tools.append(name)
        else:
            rejected_tools[name] = reason

    kept_retrievers = [name for name in final_tools if name not in DIRECT_TOOLS]
    fallback_tool: str | None = None
    fallback_reason: str | None = None
    if not kept_retrievers:
        fallback_candidate = _select_fallback_candidate(policy_candidates)
        if fallback_candidate is not None:
            fallback_tool = fallback_candidate.name
            previous_reason = rejected_tools.pop(
                fallback_tool,
                "No retriever kept after policy filter.",
            )
            if fallback_candidate.confidence_score is None:
                fallback_reason = (
                    "Policy fallback kept first known router candidate because "
                    f"all retrievers were rejected. Previous reason: {previous_reason}"
                )
            else:
                fallback_reason = (
                    "Policy fallback kept highest-confidence router candidate "
                    f"(confidence_score={fallback_candidate.confidence_score:.3f}) because "
                    f"all retrievers were rejected. Previous reason: {previous_reason}"
                )
            final_tools.append(fallback_tool)

    audit: list[str] = []
    audit.append(
        "LLM candidates: " + (", ".join(llm_candidates) if llm_candidates else "(none)")
    )
    if candidate_confidences:
        audit.append(
            "Candidate confidences: "
            + ", ".join(
                f"{name}={score:.3f}"
                for name, score in candidate_confidences.items()
            )
        )
    audit.append(
        "Final retrievers: " + (", ".join(final_tools) if final_tools else "(none)")
    )
    if fallback_tool and fallback_reason:
        audit.append(f"{fallback_tool}: fallback kept — {fallback_reason}")
    if rejected_tools:
        audit.append(
            "Policy rejected: "
            + "; ".join(f"{name} ({reason})" for name, reason in rejected_tools.items())
        )
    for tool in final_tools:
        if tool in DIRECT_TOOLS:
            audit.append(f"{tool}: direct tool kept.")
            continue
        spec = get_retriever_spec(tool)
        if not spec:
            continue
        justified, reason = retriever_is_justified(spec, prepared_question)
        if justified:
            audit.append(f"{tool}: kept — {reason}")

    return PolicyDecision(
        question=question,
        prepared_question=prepared_question,
        llm_candidates=llm_candidates,
        final_tools=final_tools,
        rejected_tools=rejected_tools,
        audit=audit,
        candidate_confidences=candidate_confidences,
        fallback_tool=fallback_tool,
        fallback_reason=fallback_reason,
    )


class RetrieverPolicy:
    """Bộ lọc loại retriever thừa từ đề xuất router agent (benchmark/test)."""

    def evaluate(
        self,
        question: str,
        llm_candidate_tools: list[str | PolicyCandidate | dict[str, Any]],
    ) -> PolicyDecision:
        return filter_retriever_candidates(question, llm_candidate_tools)


def evaluate_retriever_policy(
    question: str,
    llm_candidate_tools: list[str | PolicyCandidate | dict[str, Any]],
) -> PolicyDecision:
    return RetrieverPolicy().evaluate(question, llm_candidate_tools)
