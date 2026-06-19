from __future__ import annotations

import asyncio

from adapter.comparison_llm import (
    build_comparison_judge_llm,
    extract_message_text,
    is_retryable_gemini_error,
    GEMINI_MAX_RETRIES,
    openai_baseline_enabled,
)
from application.comparison.prompts import JUDGE_SYSTEM_PROMPT
from application.comparison.schemas import JudgeVerdict

_MISSING = "(Không có — baseline ChatGPT tạm tắt)"


def _format_user_prompt(
    question: str,
    app_answer: str,
    gpt_answer: str | None,
    gemini_answer: str | None,
) -> str:
    gpt_text = gpt_answer.strip() if gpt_answer else _MISSING
    gemini_text = gemini_answer.strip() if gemini_answer else "(Không có)"
    openai_note = ""
    if not openai_baseline_enabled() or not gpt_answer:
        openai_note = (
            "\nLưu ý: Baseline ChatGPT (OpenAI) không có trong lần so sánh này; "
            "không chọn gpt làm best hoặc winner_overall."
        )

    return (
        f"Câu hỏi người dùng:\n{question}\n\n"
        f"--- Câu trả lời APP (GraphRAG chatbot) ---\n{app_answer}\n\n"
        f"--- Câu trả lời ChatGPT baseline ---\n{gpt_text}\n\n"
        f"--- Câu trả lời Gemini baseline ---\n{gemini_text}"
        f"{openai_note}"
    )


async def judge_comparison(
    question: str,
    app_answer: str,
    gpt_answer: str | None,
    gemini_answer: str | None,
) -> JudgeVerdict:
    llm = build_comparison_judge_llm().with_structured_output(JudgeVerdict)
    messages = [
        {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": _format_user_prompt(question, app_answer, gpt_answer, gemini_answer),
        },
    ]

    last_error: Exception | None = None
    for attempt in range(GEMINI_MAX_RETRIES):
        try:
            result = await llm.ainvoke(messages)
            if isinstance(result, JudgeVerdict):
                return result
            return JudgeVerdict.model_validate(result)
        except Exception as exc:
            last_error = exc
            if not is_retryable_gemini_error(exc) or attempt >= GEMINI_MAX_RETRIES - 1:
                break
            await asyncio.sleep(1 + attempt)

    # Fallback: plain invoke + parse if structured fails
    plain_llm = build_comparison_judge_llm()
    try:
        res = await plain_llm.ainvoke(messages)
        text = extract_message_text(res.content)
        raise RuntimeError(
            f"Judge structured output failed; raw response: {text[:500]}"
        ) from last_error
    except Exception:
        if last_error is not None:
            raise last_error
        raise
