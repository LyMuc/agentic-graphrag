import asyncio
import os
import ssl
from typing import AsyncIterator

import httpx
from neo4j import GraphDatabase
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

# --- OpenAI API trực tiếp ---
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# --- Vercel AI Gateway + OpenAI-compatible API (comment để dùng lại) ---
# AI_GATEWAY_API_KEY = os.environ.get("VERCEL_AI_GATEWAY_API_KEY")
# AI_GATEWAY_BASE_URL = os.environ.get("AI_GATEWAY_BASE_URL", "https://ai-gateway.vercel.sh/v1")

RESPONSE_LLM = os.environ.get("RESPONSE_LLM", "gpt-4.1")
ROUTER_LLM = os.environ.get("ROUTER_LLM", "gpt-4o")
RETRIEVER_LLM = os.environ.get("RETRIEVER_LLM", "o3")
LLM_REQUEST_TIMEOUT = float(os.environ.get("LLM_REQUEST_TIMEOUT", "180"))
LLM_STREAM_RETRIES = int(os.environ.get("LLM_STREAM_RETRIES", "2"))

NEO4J_URI = os.environ.get('NEO4J_URI')
NEO4J_USERNAME = os.environ.get('NEO4J_USERNAME')
NEO4J_PASSWORD = os.environ.get('NEO4J_PASSWORD')
NEO4J_DATABASE = os.environ.get('NEO4J_DATABASE')

# PostgreSQL (Chainlit Data Layer)
DATABASE_URL = os.environ.get("DATABASE_URL") # format: postgresql+asyncpg://user:pass@host:port/dbname

ssl_context = ssl._create_unverified_context()

driver = GraphDatabase.driver(NEO4J_URI,
    auth=(NEO4J_USERNAME, NEO4J_PASSWORD),
    notifications_min_severity="OFF", 
)

def _normalize_openai_model(model: str) -> str:
    """Bỏ prefix openai/ khi gọi API OpenAI trực tiếp (Vercel Gateway dùng openai/...)."""
    if model.startswith("openai/"):
        return model[len("openai/") :]
    return model


def build_llm(model: str, temperature: float = 0, max_tokens: int = 2048, **kwargs) -> ChatOpenAI:
    if not OPENAI_API_KEY:
        raise ValueError("Missing OPENAI_API_KEY in environment.")
    return ChatOpenAI(
        api_key=OPENAI_API_KEY,
        model=_normalize_openai_model(model),
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=LLM_REQUEST_TIMEOUT,
        max_retries=2,
        **kwargs,
    )


# def build_llm(model: str, temperature: float = 0, max_tokens: int = 2048, **kwargs) -> ChatOpenAI:
#     if not AI_GATEWAY_API_KEY:
#         raise ValueError("Missing VERCEL_AI_GATEWAY_API_KEY in environment.")
#     return ChatOpenAI(
#         api_key=AI_GATEWAY_API_KEY,
#         base_url=AI_GATEWAY_BASE_URL,
#         model=model,
#         temperature=temperature,
#         max_tokens=max_tokens,
#         timeout=LLM_REQUEST_TIMEOUT,
#         max_retries=2,
#         **kwargs,
#     )

def build_router_llm(**kwargs) -> ChatOpenAI:
    return build_llm(model=ROUTER_LLM, temperature=0, max_tokens=2048, **kwargs)

def build_retriever_llm(**kwargs) -> ChatOpenAI:
    return build_llm(model=RETRIEVER_LLM, temperature=0, max_tokens=1024, **kwargs)

def build_response_llm(**kwargs) -> ChatOpenAI:
    return build_llm(
        model=RESPONSE_LLM,
        temperature=0,
        max_tokens=4096,
        stream_chunk_timeout=None,
        **kwargs,
    )

def _is_retryable_llm_error(exc: Exception) -> bool:
    if isinstance(
        exc,
        (
            httpx.ReadError,
            httpx.RemoteProtocolError,
            httpx.ConnectError,
            httpx.ConnectTimeout,
            httpx.ReadTimeout,
            httpx.WriteTimeout,
            httpx.PoolTimeout,
        ),
    ):
        return True

    message = str(exc).lower()
    return any(
        token in message
        for token in ("connection", "timeout", "read error", "disconnected", "reset")
    )


async def _stream_llm_tokens(llm: ChatOpenAI, messages, **config) -> AsyncIterator[str]:
    async for chunk in llm.astream(messages, **config):
        content = chunk.content
        if isinstance(content, str) and content:
            yield content

def build_structured_retriever_llm(schema):
    return build_retriever_llm().with_structured_output(schema)

# KHỞI TẠO LLM CHUNG (OpenAI API trực tiếp)
async def chat(messages, **config):
    llm = build_llm(model=RESPONSE_LLM, temperature=0, max_tokens=2048)
    res = await llm.ainvoke(messages, **config)
    return res.content


async def chat_stream(messages, **config) -> AsyncIterator[str]:
    llm = build_response_llm()
    last_error: Exception | None = None

    for attempt in range(LLM_STREAM_RETRIES):
        try:
            async for token in _stream_llm_tokens(llm, messages, **config):
                yield token
            return
        except Exception as exc:
            if not _is_retryable_llm_error(exc):
                raise
            last_error = exc
            if attempt < LLM_STREAM_RETRIES - 1:
                await asyncio.sleep(1 + attempt)

    try:
        res = await llm.ainvoke(messages, **config)
        content = res.content if hasattr(res, "content") else str(res)
        if isinstance(content, str) and content:
            yield content
            return
    except Exception as invoke_error:
        if last_error is not None:
            raise last_error from invoke_error
        raise

    if last_error is not None:
        raise last_error


# =============================================================================
# Cấu hình Gemini API trực tiếp (tạm comment — server thường bị 503 high demand)
# =============================================================================
# from typing import Callable
# from langchain_google_genai import ChatGoogleGenerativeAI
#
# GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
#
# RESPONSE_LLM = os.environ.get("RESPONSE_LLM", "gemini-3.5-flash")
# ROUTER_LLM = os.environ.get("ROUTER_LLM", "gemini-3.1-flash-lite")
# RETRIEVER_LLM = os.environ.get("RETRIEVER_LLM", "gemini-3.1-flash-lite")
# CHAT_LLM = os.environ.get("CHAT_LLM", "gemini-2.5-flash-lite")
#
# RETRIEVER_THINKING_BUDGET = int(os.environ.get("RETRIEVER_THINKING_BUDGET", "4096"))
# RETRIEVER_THINKING_LEVEL = os.environ.get("RETRIEVER_THINKING_LEVEL", "low")
# RESPONSE_THINKING_BUDGET = int(os.environ.get("RESPONSE_THINKING_BUDGET", "2048"))
# RESPONSE_THINKING_LEVEL = os.environ.get("RESPONSE_THINKING_LEVEL", "low")
#
# def _parse_model_list(primary: str, env_key: str, default: str) -> list[str]:
#     models = [primary.strip()]
#     for model in os.environ.get(env_key, default).split(","):
#         model = model.strip()
#         if model and model not in models:
#             models.append(model)
#     return models
#
# ROUTER_MODELS = _parse_model_list(ROUTER_LLM, "ROUTER_FALLBACK_LLMS", "gemini-2.5-flash-lite,gemini-3.5-flash")
# RETRIEVER_MODELS = _parse_model_list(RETRIEVER_LLM, "RETRIEVER_FALLBACK_LLMS", "gemini-2.5-flash-lite")
# RESPONSE_MODELS = _parse_model_list(RESPONSE_LLM, "RESPONSE_FALLBACK_LLMS", "gemini-3.1-flash-lite,gemini-2.5-flash")
#
# def _build_gemini_llm(model: str, temperature: float = 0, max_tokens: int = 2048, **kwargs) -> ChatGoogleGenerativeAI:
#     if not GOOGLE_API_KEY:
#         raise ValueError("Missing GOOGLE_API_KEY or GEMINI_API_KEY in environment.")
#     return ChatGoogleGenerativeAI(
#         api_key=GOOGLE_API_KEY,
#         model=model,
#         temperature=temperature,
#         max_tokens=max_tokens,
#         **kwargs,
#     )
#
# def _is_gemini_3_model(model: str) -> bool:
#     return model.startswith("gemini-3")
#
# def _thinking_kwargs_for_model(model: str, *, budget: int | None = None, level: str | None = None) -> dict:
#     if _is_gemini_3_model(model):
#         if level:
#             return {"thinking_level": level, "include_thoughts": False}
#         return {}
#     if budget is not None:
#         return {"thinking_budget": budget}
#     return {"thinking_budget": 0}
#
# def _is_retryable_gemini_error(exc: Exception) -> bool:
#     message = str(exc).lower()
#     return any(token in message for token in ("503", "unavailable", "high demand", "resource exhausted"))
#
# def _extract_text_content(content) -> str:
#     if isinstance(content, str):
#         return content
#     if isinstance(content, list):
#         text_parts = []
#         for part in content:
#             if isinstance(part, str):
#                 text_parts.append(part)
#             elif isinstance(part, dict) and part.get("type") == "text":
#                 text_parts.append(part.get("text", ""))
#         return "".join(text_parts)
#     return ""
#
# async def ainvoke_structured_retriever(schema, messages):
#     ...
#
# async def ainvoke_router_with_tools(messages, tools):
#     ...
