"""Thực thi / tái sử dụng tool call (deterministic) + render Chainlit step.

Tách từ ``application/router.py`` trong Phase 4 refactor. Không tự giữ state;
mọi state (retrieval_memory) được truyền vào từ ConversationOrchestrator.
"""
from __future__ import annotations

import asyncio
from typing import Any, Iterable

from server.domain.legal.bundle import process_context_strings
from server.agents.router.catalog import DIRECT_TOOLS
from server.agents.router.schema import (
    _resolved_query,
    _tool_call_name,
    _tool_function_args,
    _unique_tool_calls,
    _validate_registered_tools,
)
from server.conversation.memory import current_kg_version, validate_reuse_request


def _render_retriever_contexts_for_ui(contexts: Iterable[Any]) -> str:
    """Render encoded bundles / legacy context strings for Chainlit retriever steps."""

    pipeline = process_context_strings(contexts)
    return pipeline.rendered_text or "Khong tim thay context phu hop."


async def _execute_tool_call(
    tools: dict[str, Any],
    tool_call: dict[str, Any],
    updated_question: str,
    *,
    cache_fallback_reason: str = "",
) -> Any:
    """Execute one registered tool and optionally expose a Chainlit trace.

    Returns:
        Raw tool result. Dictionary results are annotated with
        ``retriever_name``. Retriever steps show rendered legal context for
        the UI; template debug text is kept in step metadata when present.

    Raises:
        RuntimeError: If the selected tool is not registered.
    """
    import chainlit as cl

    tool_name = _tool_call_name(tool_call)
    if tool_name not in tools:
        raise RuntimeError(
            f"Tool '{tool_name}' is not registered. Register the retriever in tools."
        )

    function_to_call = tools[tool_name]["function"]
    function_args, resolved_query = _tool_function_args(
        tools,
        tool_call,
        updated_question,
    )

    async def _run() -> Any:
        res = await function_to_call(**function_args)
        if isinstance(res, dict):
            res["retriever_name"] = tool_name
            res["resolved_query"] = resolved_query
            res["cache_status"] = "retrieved"
            if cache_fallback_reason:
                res["cache_fallback_reason"] = cache_fallback_reason
        return res

    async with cl.Step(name=f"Retriever: {tool_name}") as step:
        step.input = f"Tool Input: {function_args}"
        res = await _run()
        if isinstance(res, dict) and "contexts" in res:
            step.output = _render_retriever_contexts_for_ui(res["contexts"])
        elif isinstance(res, list):
            parts = [str(item) for item in res if item is not None]
            step.output = (
                "\n\n".join(parts)
                if parts
                else "Khong tim thay context phu hop."
            )
        else:
            step.output = str(res)
        metadata: dict[str, Any] = {"raw_result": res}
        if isinstance(res, dict):
            debug = (res.get("debug") or "").strip()
            if debug:
                metadata["retrieval_debug"] = debug
        step.metadata = metadata
        return res


async def _reuse_tool_call(
    tool_call: dict[str, Any],
    validation_contexts: list[str],
    context_refs: list[str],
    updated_question: str,
) -> dict[str, Any]:
    """Return validated cached contexts through a visible Chainlit retriever step."""

    import chainlit as cl

    tool_name = _tool_call_name(tool_call)
    resolved_query = _resolved_query(tool_call, updated_question)
    result: dict[str, Any] = {
        "contexts": validation_contexts,
        "debug": (
            "Context cache reused.\n"
            f"Refs: {', '.join(context_refs)}\n"
            f"Resolved query: {resolved_query}"
        ),
        "retriever_name": tool_name,
        "resolved_query": resolved_query,
        "cache_status": "reused",
        "context_refs_used": context_refs,
    }

    async with cl.Step(name=f"Retriever cache: {tool_name}") as step:
        step.input = {
            "resolved_query": resolved_query,
            "context_refs": context_refs,
        }
        step.output = _render_retriever_contexts_for_ui(validation_contexts)
        step.metadata = {
            "raw_result": result,
            "retrieval_debug": result["debug"],
        }
    return result


async def _execute_or_reuse_tool_call(
    tools: dict[str, Any],
    tool_call: dict[str, Any],
    updated_question: str,
    *,
    retrieval_memory: dict[str, dict[str, Any]],
    thread_id: str,
    kg_version: str,
) -> Any:
    """Reuse validated context or execute the selected tool as a fallback."""

    tool_name = _tool_call_name(tool_call)
    if tool_name in DIRECT_TOOLS:
        return await _execute_tool_call(tools, tool_call, updated_question)
    validation = validate_reuse_request(
        tool_name=tool_name,
        tool_args=dict(tool_call.get("args", {})),
        memory=retrieval_memory,
        thread_id=thread_id,
        kg_version=kg_version,
    )
    if validation.allowed:
        return await _reuse_tool_call(
            tool_call,
            validation.contexts,
            validation.context_refs,
            updated_question,
        )
    requested_reuse = (
        str((tool_call.get("args") or {}).get("context_action") or "retrieve")
        == "reuse"
    )
    return await _execute_tool_call(
        tools,
        tool_call,
        updated_question,
        cache_fallback_reason=validation.reason if requested_reuse else "",
    )


async def handle_tool_calls(
    tools: dict[str, Any],
    tool_calls: list[dict[str, Any]],
    updated_question: str,
    *,
    retrieval_memory: dict[str, dict[str, Any]] | None = None,
    thread_id: str = "",
    kg_version: str | None = None,
) -> list[Any]:
    """Execute policy-approved calls concurrently with deterministic cache reuse.

    Returns:
        Results ordered like the unique tool calls. An empty call list returns
        an empty result list.
    """

    if not tool_calls:
        return []

    unique_tool_calls = _unique_tool_calls(tool_calls)
    _validate_registered_tools(tools, unique_tool_calls)
    print("policy_tool_calls:", unique_tool_calls)

    return list(
        await asyncio.gather(
            *(
                _execute_or_reuse_tool_call(
                    tools,
                    tool_call,
                    updated_question,
                    retrieval_memory=retrieval_memory or {},
                    thread_id=thread_id,
                    kg_version=kg_version or current_kg_version(),
                )
                for tool_call in unique_tool_calls
            )
        )
    )
