"""Tool schema cho Router LLM: thêm confidence + control args, lọc args.

Tách từ ``application/router.py`` trong Phase 4 refactor. Logic xác định
(deterministic) build/validate schema, không gọi LLM.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from server.agents.router.catalog import DIRECT_TOOLS
from server.agents.router.prompt import RETRIEVER_QUERY_PARAM_DESCRIPTION

ROUTER_ONLY_ARGS = {"confidence_score"}


def _tool_accepts_query(tools: dict[str, Any], tool_name: str) -> bool:
    """Check whether a registered tool schema declares a ``query`` argument."""

    properties = (
        tools[tool_name]["description"]
        .get("function", {})
        .get("parameters", {})
        .get("properties", {})
    )
    return "query" in properties


def _tool_call_name(tool_call: dict[str, Any]) -> str:
    """Extract a normalized tool name from a Router call."""

    return str(tool_call.get("name", ""))


def _tool_schema_name(schema: dict[str, Any]) -> str:
    """Lấy tên function tool từ schema truyền cho Router LLM."""
    return str(schema.get("function", {}).get("name", ""))


def _with_router_confidence_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Thêm optional confidence_score vào schema retriever gửi cho Router LLM."""
    out = deepcopy(schema)
    tool_name = _tool_schema_name(out)
    if not tool_name or tool_name in DIRECT_TOOLS:
        return out

    function_schema = out.get("function")
    if not isinstance(function_schema, dict):
        return out

    parameters = function_schema.setdefault("parameters", {})
    if not isinstance(parameters, dict):
        return out
    parameters.setdefault("type", "object")

    properties = parameters.setdefault("properties", {})
    if not isinstance(properties, dict):
        return out
    properties["confidence_score"] = {
        "type": "number",
        "minimum": 0.0,
        "maximum": 1.0,
        "description": (
            "Điểm tự tin từ 0.0 đến 1.0 cho biết mức chắc chắn retriever này "
            "cần thiết để trả lời câu hỏi. Đây là metadata định tuyến."
        ),
    }
    return out


def _strip_router_only_args(args: dict[str, Any]) -> dict[str, Any]:
    """Loại metadata chỉ dùng cho router trước khi gọi function thật."""
    return {key: value for key, value in args.items() if key not in ROUTER_ONLY_ARGS}


def _unique_tool_calls(tool_calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove duplicate Router calls while preserving first-tool order."""

    seen_tools: set[str] = set()
    unique_tool_calls: list[dict[str, Any]] = []
    for tool_call in tool_calls:
        tool_name = _tool_call_name(tool_call)
        if not tool_name or tool_name in seen_tools:
            continue
        seen_tools.add(tool_name)
        unique_tool_calls.append(tool_call)
    return unique_tool_calls


def _validate_registered_tools(tools: dict[str, Any], tool_calls: list[dict[str, Any]]) -> None:
    """Ensure every router-selected tool exists in the runtime registry.

    Raises:
        RuntimeError: If one or more selected tools are missing.
    """

    missing = [
        _tool_call_name(call)
        for call in tool_calls
        if _tool_call_name(call) not in tools
    ]
    if missing:
        missing_list = ", ".join(sorted(set(missing)))
        raise RuntimeError(
            "Router selected tool(s) that are not registered in tools: "
            f"{missing_list}. Register the corresponding retriever(s) before routing."
        )


def _router_tool_descriptions(tools: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Build Router schemas with routing confidence and context controls.

    Args:
        tools: Optional runtime registry. When supplied, only registered tools
            are exposed; otherwise the catalog registry is used.

    Returns:
        Deep-copied OpenAI tool schemas. Non-direct retrievers receive optional
        ``confidence_score``, ``context_action``, ``context_refs``,
        ``time_scope``, and ``target_date`` properties without mutating their
        original descriptions.
    """
    if tools:
        descriptions = [
            deepcopy(entry["description"])
            for entry in tools.values()
            if isinstance(entry, dict) and "description" in entry
        ]
    else:
        from server.interface.router_tools import router_tools_for_llm

        descriptions = deepcopy(router_tools_for_llm())

    descriptions = [
        _with_router_confidence_schema(description)
        for description in descriptions
    ]
    for description in descriptions:
        function = description.get("function") or {}
        tool_name = str(function.get("name") or "")
        if tool_name in DIRECT_TOOLS:
            continue
        parameters = function.setdefault("parameters", {"type": "object"})
        properties = parameters.setdefault("properties", {})
        properties["context_action"] = {
            "type": "string",
            "enum": ["retrieve", "reuse"],
            "description": "Retrieve mới hoặc tái sử dụng context_ref đã có.",
        }
        properties["context_refs"] = {
            "type": "array",
            "items": {"type": "string"},
            "description": "Các context_ref cần tái sử dụng; để rỗng khi retrieve.",
        }
        properties["time_scope"] = {
            "type": "string",
            "enum": ["current", "explicit", "ambiguous"],
            "description": "Phạm vi thời gian áp dụng pháp luật.",
        }
        properties["target_date"] = {
            "type": "string",
            "description": "Ngày YYYY-MM-DD hoặc năm YYYY khi time_scope=explicit.",
        }
        if "query" in properties:
            properties["query"]["description"] = RETRIEVER_QUERY_PARAM_DESCRIPTION
    return descriptions


_CONTROL_ARGS = ROUTER_ONLY_ARGS | {
    "context_action",
    "context_refs",
    "time_scope",
    "target_date",
}


def _resolved_query(tool_call: dict[str, Any], fallback_question: str) -> str:
    """Return the Router-resolved standalone query for one tool call."""

    args = tool_call.get("args") or {}
    query = str(args.get("query") or "").strip()
    return query or fallback_question


def _tool_function_args(
    tools: dict[str, Any],
    tool_call: dict[str, Any],
    fallback_question: str,
) -> tuple[dict[str, Any], str]:
    """Build callable arguments without Router-only cache controls.

    Returns:
        Tuple ``(function_args, resolved_query)``. The Router's standalone
        ``query`` is preserved, while cache/time control fields are removed so
        retriever call signatures remain unchanged.
    """

    tool_name = _tool_call_name(tool_call)
    router_args = dict(tool_call.get("args", {}))
    function_args = {
        key: value
        for key, value in router_args.items()
        if key not in _CONTROL_ARGS
    }
    resolved_query = _resolved_query(tool_call, fallback_question)
    if _tool_accepts_query(tools, tool_name):
        function_args["query"] = resolved_query
    return function_args, resolved_query
