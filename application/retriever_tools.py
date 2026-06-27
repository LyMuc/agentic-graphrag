"""Build Chainlit tool registry from adapter retrievers and direct tools."""
from __future__ import annotations

import importlib
from collections.abc import Callable
from typing import Any

from adapter.direct_tools import (
    answer_given,
    answer_given_description,
    clarify_description,
    clarify_question,
)
from application.adapter_router_descriptions import ADAPTER_DESCRIPTION_SOURCES
from application.retriever_catalog import PRIMARY_RETRIEVER_SPECS


def _load_retriever_callable(module_path: str, function_name: str) -> Callable[..., Any]:
    module = importlib.import_module(module_path)
    fn = getattr(module, function_name, None)
    if not callable(fn):
        raise AttributeError(f"{module_path} missing callable {function_name}")
    return fn


def build_presentation_tools() -> dict[str, dict[str, Any]]:
    """Return the full tool map used by presentation/main.py and the Router."""
    tools: dict[str, dict[str, Any]] = {}

    for name in PRIMARY_RETRIEVER_SPECS:
        source = ADAPTER_DESCRIPTION_SOURCES.get(name)
        if source is None:
            continue
        module_path, description_attr = source
        module = importlib.import_module(module_path)
        description = getattr(module, description_attr)
        function = _load_retriever_callable(module_path, name)
        tools[name] = {"description": description, "function": function}

    tools["respond"] = {
        "description": answer_given_description,
        "function": answer_given,
    }
    tools["clarify"] = {
        "description": clarify_description,
        "function": clarify_question,
    }
    return tools
