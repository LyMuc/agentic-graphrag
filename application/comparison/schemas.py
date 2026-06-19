from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

WinnerLabel = Literal["app", "gpt", "gemini", "tie", "unclear"]
OverallWinner = Literal["app", "gpt", "gemini", "tie", "unclear"]


class CriterionComparison(BaseModel):
    best: WinnerLabel = Field(description="Answer tốt hơn cho tiêu chí này")
    app_note: str = Field(description="Ghi chú ngắn về câu trả lời app")
    gpt_note: str = Field(description="Ghi chú ngắn về câu trả lời ChatGPT baseline")
    gemini_note: str = Field(description="Ghi chú ngắn về câu trả lời Gemini baseline")
    comparison_vi: str = Field(description="So sánh ngắn tiêu chí này")


class JudgeVerdict(BaseModel):
    citation_detail: CriterionComparison
    validity_warnings: CriterionComparison
    problem_accuracy: CriterionComparison
    winner_overall: OverallWinner
    summary_vi: str = Field(description="Tóm tắt 2–4 câu cho người dùng")


class ComparisonInput(BaseModel):
    question: str
    app_answer: str


class ComparisonResult(BaseModel):
    question: str
    app_answer: str
    gpt_answer: str | None = None
    gemini_answer: str | None = None
    verdict: JudgeVerdict
    openai_baseline_skipped: bool = False
    openai_baseline_note: str = ""
