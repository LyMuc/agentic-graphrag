from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class PolicyCandidate:
    """Một retriever candidate do Router Agent đề xuất kèm độ tự tin tùy chọn."""

    name: str
    confidence_score: float | None = None


@dataclass
class PolicyDecision:
    """Kết quả đánh giá retriever candidates sau khi áp dụng policy."""

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
        return asdict(self)

    def audit_text(self) -> str:
        if not self.audit:
            return "RetrieverPolicy: khong co audit."
        return "\n".join(f"- {line}" for line in self.audit)
