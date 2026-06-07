from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from application.retriever_catalog import (
    DIRECT_TOOLS,
    RetrieverSpec,
    TriggerRule,
    get_retriever_spec,
    prepare_question,
)


@dataclass
class PolicyDecision:
    question: str
    prepared_question: str
    llm_candidates: list[str]
    final_tools: list[str]
    rejected_tools: dict[str, str]
    audit: list[str]

    def to_dict(self) -> dict[str, Any]:
        """Chuyển decision sang dict để log hoặc benchmark.

        Returns:
            Dict serializable.
        """
        return asdict(self)

    def audit_text(self) -> str:
        """Format audit cho hiển thị UI.

        Returns:
            Chuỗi nhiều dòng mô tả quyết định policy.
        """
        if not self.audit:
            return "RetrieverPolicy: khong co audit."
        return "\n".join(f"- {line}" for line in self.audit)


def _unique(items: list[str]) -> list[str]:
    """Loại trùng tên tool, giữ thứ tự xuất hiện đầu tiên.

    Args:
        items: Danh sách tên tool.

    Returns:
        Danh sách không trùng.
    """
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def _matching_rules(
    rules: tuple[TriggerRule, ...],
    prepared_question: str,
) -> list[TriggerRule]:
    """Lọc các trigger rule khớp phrase với câu hỏi.

    Args:
        rules: Required hoặc support triggers của spec.
        prepared_question: Câu hỏi đã prepare.

    Returns:
        Các rule đã khớp.
    """
    return [rule for rule in rules if rule.matches(prepared_question)]


def retriever_is_justified(
    spec: RetrieverSpec,
    prepared_question: str,
) -> tuple[bool, str]:
    """Kiểm tra retriever có >=1 required hoặc support trigger khớp.

    Args:
        spec: RetrieverSpec từ catalog.
        prepared_question: Câu hỏi đã prepare.

    Returns:
        (justified, reason) — reason mô tả rule khớp hoặc lý do loại.
    """
    required_hits = _matching_rules(spec.required_triggers, prepared_question)
    if required_hits:
        return True, required_hits[0].reason

    support_hits = _matching_rules(spec.support_triggers, prepared_question)
    if support_hits:
        return True, support_hits[0].reason

    return False, "No required/support trigger match."


def filter_retriever_candidates(
    question: str,
    llm_candidate_tools: list[str],
) -> PolicyDecision:
    """Lọc danh sách router agent, loại retriever thừa, giữ tên gốc.

    Args:
        question: Câu hỏi người dùng.
        llm_candidate_tools: Tên retriever router agent đề xuất.

    Returns:
        PolicyDecision với final_tools là subset đã lọc.
    """
    prepared_question = prepare_question(question)
    llm_candidates = _unique([str(name) for name in llm_candidate_tools if name])

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

    audit: list[str] = []
    audit.append(
        "LLM candidates: " + (", ".join(llm_candidates) if llm_candidates else "(none)")
    )
    audit.append(
        "Final retrievers: " + (", ".join(final_tools) if final_tools else "(none)")
    )
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
    )


class RetrieverPolicy:
    """Bộ lọc loại retriever thừa từ đề xuất router agent."""

    def evaluate(self, question: str, llm_candidate_tools: list[str]) -> PolicyDecision:
        """Chạy filter policy trên danh sách candidate.

        Args:
            question: Câu hỏi người dùng.
            llm_candidate_tools: Tên tool router đề xuất.

        Returns:
            PolicyDecision đã lọc.
        """
        return filter_retriever_candidates(question, llm_candidate_tools)


def evaluate_retriever_policy(
    question: str,
    llm_candidate_tools: list[str],
) -> PolicyDecision:
    """API tiện ích gọi RetrieverPolicy.

    Args:
        question: Câu hỏi người dùng.
        llm_candidate_tools: Tên tool router đề xuất.

    Returns:
        PolicyDecision đã lọc.
    """
    return RetrieverPolicy().evaluate(question, llm_candidate_tools)
