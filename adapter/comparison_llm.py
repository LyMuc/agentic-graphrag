"""LLM builders for baseline comparison (isolated from main app OpenAI/Gemini config)."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from adapter.config import LLM_REQUEST_TIMEOUT, build_llm

load_dotenv()

COMPARISON_ENABLED = os.environ.get("COMPARISON_ENABLED", "true").lower() in ("1", "true", "yes")
COMPARISON_USE_OPENAI = os.environ.get("COMPARISON_USE_OPENAI", "true").lower() in ("1", "true", "yes")

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
BASELINE_GEMINI_MODEL = os.environ.get("BASELINE_GEMINI_MODEL", "gemini-2.5-flash")
JUDGE_GEMINI_MODEL = os.environ.get("JUDGE_GEMINI_MODEL", "gemini-2.5-flash")
BASELINE_OPENAI_MODEL = os.environ.get("BASELINE_OPENAI_MODEL", "gpt-4.1")

GEMINI_MAX_RETRIES = int(os.environ.get("COMPARISON_GEMINI_RETRIES", "2"))
OPENAI_MAX_RETRIES = int(os.environ.get("COMPARISON_OPENAI_RETRIES", "2"))


def comparison_is_enabled() -> bool:
    return COMPARISON_ENABLED


def openai_baseline_enabled() -> bool:
    return COMPARISON_USE_OPENAI


def build_comparison_gemini_llm(
    model: str,
    temperature: float = 0,
    max_tokens: int = 4096,
    **kwargs,
) -> ChatGoogleGenerativeAI:
    if not GOOGLE_API_KEY:
        raise ValueError("Missing GOOGLE_API_KEY or GEMINI_API_KEY for comparison.")
    return ChatGoogleGenerativeAI(
        api_key=GOOGLE_API_KEY,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=LLM_REQUEST_TIMEOUT,
        **kwargs,
    )


def build_comparison_openai_llm(model: str) -> ChatOpenAI:
    return build_llm(model=model, temperature=0, max_tokens=4096)


def build_comparison_judge_llm() -> ChatGoogleGenerativeAI:
    return build_comparison_gemini_llm(model=JUDGE_GEMINI_MODEL, max_tokens=4096)


def extract_message_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict) and part.get("type") == "text":
                parts.append(str(part.get("text", "")))
        return "".join(parts)
    return str(content) if content is not None else ""


def is_retryable_gemini_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return any(
        token in message
        for token in ("503", "unavailable", "high demand", "resource exhausted", "timeout")
    )
