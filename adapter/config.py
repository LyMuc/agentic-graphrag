"""Back-compat shim — đã tách trong Phase 2 refactor.

- LLM factory  -> ``server.infrastructure.llm.factory``
- Neo4j driver -> ``server.infrastructure.neo4j.client``

Mọi import cũ ``from adapter.config import ...`` vẫn hoạt động cho tới khi các
call site (retrievers, scripts, router) chuyển sang đường dẫn mới ở các phase sau.
"""
from __future__ import annotations

import os

from server.infrastructure.neo4j.client import (
    NEO4J_DATABASE,
    NEO4J_PASSWORD,
    NEO4J_URI,
    NEO4J_USERNAME,
    driver,
    ssl_context,
)
from server.infrastructure.llm.factory import (
    LLM_REQUEST_TIMEOUT,
    LLM_STREAM_RETRIES,
    OPENAI_API_KEY,
    RESPONSE_LLM,
    RETRIEVER_LLM,
    ROUTER_LLM,
    _is_retryable_llm_error,
    _normalize_openai_model,
    _stream_llm_tokens,
    build_llm,
    build_response_llm,
    build_retriever_llm,
    build_router_llm,
    build_structured_retriever_llm,
    chat,
    chat_stream,
)

# PostgreSQL (Chainlit Data Layer) — giữ ở shim để back-compat; nguồn thật ở
# server.infrastructure.persistence.data_layer (đọc cùng biến môi trường).
DATABASE_URL = os.environ.get("DATABASE_URL")


import warnings as _warnings

_warnings.warn(
    f"{__name__} là shim back-compat (refactor sang cây server/); "
    "hãy import từ vị trí server.* mới. Shim sẽ bị gỡ ở PR sau.",
    DeprecationWarning,
    stacklevel=2,
)
