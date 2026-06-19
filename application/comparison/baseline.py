from __future__ import annotations

import asyncio

from adapter.comparison_llm import (
    BASELINE_GEMINI_MODEL,
    BASELINE_OPENAI_MODEL,
    COMPARISON_USE_OPENAI,
    OPENAI_MAX_RETRIES,
    build_comparison_openai_llm,
    build_comparison_gemini_llm,
    extract_message_text,
    is_retryable_gemini_error,
    GEMINI_MAX_RETRIES,
)
from application.comparison.prompts import BASELINE_SYSTEM_PROMPT


def _baseline_messages(question: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": BASELINE_SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]


async def fetch_openai_baseline(question: str) -> str | None:
    if not COMPARISON_USE_OPENAI:
        return None

    llm = build_comparison_openai_llm(BASELINE_OPENAI_MODEL)
    messages = _baseline_messages(question)
    last_error: Exception | None = None

    for attempt in range(OPENAI_MAX_RETRIES):
        try:
            res = await llm.ainvoke(messages)
            return extract_message_text(res.content).strip() or None
        except Exception as exc:
            last_error = exc
            if attempt >= OPENAI_MAX_RETRIES - 1:
                return None
            await asyncio.sleep(1 + attempt)

    if last_error is not None:
        return None
    return None


async def fetch_gemini_baseline(question: str) -> str | None:
    llm = build_comparison_gemini_llm(model=BASELINE_GEMINI_MODEL)
    messages = _baseline_messages(question)
    last_error: Exception | None = None

    for attempt in range(GEMINI_MAX_RETRIES):
        try:
            res = await llm.ainvoke(messages)
            text = extract_message_text(res.content).strip()
            return text or None
        except Exception as exc:
            last_error = exc
            if not is_retryable_gemini_error(exc) or attempt >= GEMINI_MAX_RETRIES - 1:
                raise
            await asyncio.sleep(1 + attempt)

    if last_error is not None:
        raise last_error
    return None
