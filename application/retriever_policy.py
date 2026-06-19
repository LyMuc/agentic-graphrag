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
class PolicyCandidate:
    """Một retriever candidate do Router Agent đề xuất kèm độ tự tin tùy chọn.

    Args:
        name: Tên tool/retriever gốc do Router Agent trả về.
        confidence_score: Điểm tự tin trong khoảng 0.0-1.0 nếu router cung cấp.

    Returns:
        Dataclass dùng làm input chuẩn hóa cho RetrieverPolicy.
    """

    name: str
    confidence_score: float | None = None


@dataclass
class PolicyDecision:
    """Kết quả đánh giá retriever candidates sau khi áp dụng policy.

    Args:
        question: Câu hỏi gốc của người dùng.
        prepared_question: Câu hỏi đã chuẩn hóa để so khớp phrase.
        llm_candidates: Danh sách tên tool router đề xuất sau khi loại trùng.
        final_tools: Danh sách tool cuối cùng được phép chạy.
        rejected_tools: Map tool bị loại tới lý do loại.
        audit: Các dòng log ngắn để hiển thị/debug.
        candidate_confidences: Map tên retriever tới confidence_score hợp lệ nếu có.
        fallback_tool: Tên retriever được rescue khi policy lọc rỗng, nếu có.
        fallback_reason: Lý do fallback, nếu có.

    Returns:
        Dataclass serializable dùng cho Chainlit metadata, benchmark và debug.
    """

    question: str
    prepared_question: str
    llm_candidates: list[str]
    final_tools: list[str]
    rejected_tools: dict[str, str]
    audit: list[str]
    candidate_confidences: dict[str, float] | None = None
    fallback_tool: str | None = None
    fallback_reason: str | None = None

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


def _coerce_confidence(value: Any) -> float | None:
    """Chuẩn hóa confidence_score từ Router Agent về khoảng 0.0-1.0.

    Args:
        value: Giá trị thô từ tool args hoặc PolicyCandidate.

    Returns:
        Float đã clamp trong khoảng 0.0-1.0, hoặc None nếu thiếu/không parse được.
    """
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
    """Chuyển một input candidate bất kỳ về PolicyCandidate chuẩn.

    Args:
        item: Tên tool dạng chuỗi, PolicyCandidate, hoặc dict có name/tool_name và
            confidence_score.

    Returns:
        PolicyCandidate hợp lệ, hoặc None nếu thiếu tên tool.
    """
    if isinstance(item, PolicyCandidate):
        name = str(item.name or "").strip()
        if not name:
            return None
        return PolicyCandidate(name=name, confidence_score=_coerce_confidence(item.confidence_score))

    if isinstance(item, dict):
        raw_name = item.get("name") or item.get("tool_name")
        name = str(raw_name or "").strip()
        if not name:
            return None
        return PolicyCandidate(
            name=name,
            confidence_score=_coerce_confidence(item.get("confidence_score")),
        )

    name = str(item or "").strip()
    if not name:
        return None
    return PolicyCandidate(name=name)


def _unique_policy_candidates(
    candidates: list[str | PolicyCandidate | dict[str, Any]],
) -> list[PolicyCandidate]:
    """Loại trùng retriever candidates nhưng giữ thứ tự xuất hiện đầu tiên.

    Args:
        candidates: Danh sách tên tool hoặc PolicyCandidate từ Router Agent.

    Returns:
        Danh sách PolicyCandidate đã chuẩn hóa, không trùng tên tool.
    """
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
    """Tạo map confidence hợp lệ để lưu vào audit và metadata.

    Args:
        candidates: Danh sách PolicyCandidate đã chuẩn hóa.

    Returns:
        Dict tên tool tới confidence_score, chỉ gồm các score parse được.
    """
    return {
        candidate.name: candidate.confidence_score
        for candidate in candidates
        if candidate.confidence_score is not None
    }


def _select_fallback_candidate(candidates: list[PolicyCandidate]) -> PolicyCandidate | None:
    """Chọn retriever known tốt nhất khi policy phrase-based lọc rỗng.

    Args:
        candidates: Danh sách candidate router đề xuất sau khi loại trùng.

    Returns:
        PolicyCandidate known retriever có confidence_score cao nhất, hoặc known
        retriever đầu tiên nếu mọi score đều thiếu/không hợp lệ. Không trả về direct
        tool hoặc unknown retriever.
    """
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
    llm_candidate_tools: list[str | PolicyCandidate | dict[str, Any]],
) -> PolicyDecision:
    """Lọc danh sách router agent, loại retriever thừa, giữ tên gốc.

    Args:
        question: Câu hỏi người dùng.
        llm_candidate_tools: Tên retriever hoặc PolicyCandidate router agent đề xuất.

    Returns:
        PolicyDecision với final_tools đã lọc; nếu mọi retriever known bị loại thì
        fallback giữ retriever có confidence_score cao nhất hoặc retriever known đầu tiên.
    """
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
            previous_reason = rejected_tools.pop(fallback_tool, "No retriever kept after policy filter.")
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
    """Bộ lọc loại retriever thừa từ đề xuất router agent."""

    def evaluate(
        self,
        question: str,
        llm_candidate_tools: list[str | PolicyCandidate | dict[str, Any]],
    ) -> PolicyDecision:
        """Chạy filter policy trên danh sách candidate.

        Args:
            question: Câu hỏi người dùng.
            llm_candidate_tools: Tên tool hoặc PolicyCandidate router đề xuất.

        Returns:
            PolicyDecision đã lọc.
        """
        return filter_retriever_candidates(question, llm_candidate_tools)


def evaluate_retriever_policy(
    question: str,
    llm_candidate_tools: list[str | PolicyCandidate | dict[str, Any]],
) -> PolicyDecision:
    """API tiện ích gọi RetrieverPolicy.

    Args:
        question: Câu hỏi người dùng.
        llm_candidate_tools: Tên tool hoặc PolicyCandidate router đề xuất.

    Returns:
        PolicyDecision đã lọc.
    """
    return RetrieverPolicy().evaluate(question, llm_candidate_tools)
