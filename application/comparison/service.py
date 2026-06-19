from __future__ import annotations

import asyncio

from adapter.comparison_llm import COMPARISON_USE_OPENAI, openai_baseline_enabled
from application.comparison.baseline import fetch_gemini_baseline, fetch_openai_baseline
from application.comparison.judge import judge_comparison
from application.comparison.schemas import ComparisonInput, ComparisonResult


async def run_comparison(data: ComparisonInput) -> ComparisonResult:
    question = data.question.strip()
    app_answer = data.app_answer.strip()

    gpt_task = asyncio.create_task(fetch_openai_baseline(question))
    gemini_task = asyncio.create_task(fetch_gemini_baseline(question))

    gpt_answer, gemini_answer = await asyncio.gather(gpt_task, gemini_task)

    openai_skipped = not openai_baseline_enabled() or gpt_answer is None
    openai_note = ""
    if not COMPARISON_USE_OPENAI:
        openai_note = "ChatGPT baseline tạm tắt (COMPARISON_USE_OPENAI=false / hết quota OpenAI)."
    elif gpt_answer is None:
        openai_note = "ChatGPT baseline không trả về nội dung."

    if gemini_answer is None:
        raise RuntimeError("Không lấy được câu trả lời baseline từ Gemini.")

    verdict = await judge_comparison(
        question=question,
        app_answer=app_answer,
        gpt_answer=gpt_answer,
        gemini_answer=gemini_answer,
    )

    return ComparisonResult(
        question=question,
        app_answer=app_answer,
        gpt_answer=gpt_answer,
        gemini_answer=gemini_answer,
        verdict=verdict,
        openai_baseline_skipped=openai_skipped,
        openai_baseline_note=openai_note,
    )
