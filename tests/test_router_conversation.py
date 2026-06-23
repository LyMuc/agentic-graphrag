from __future__ import annotations

from copy import deepcopy

from application.router import (
    _evaluate_tool_calls_policy,
    _router_tool_descriptions,
    _tool_function_args,
)
from adapter.direct_tools import clarify_question


def _tool_schema(name: str) -> dict:
    """Build one minimal query-based Router tool schema.

    Args:
        name: Tool/function name.

    Returns:
        Runtime registry entry containing a function schema and placeholder
        callable.
    """

    return {
        "description": {
            "type": "function",
            "function": {
                "name": name,
                "description": "test",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
            },
        },
        "function": lambda **kwargs: kwargs,
    }


def test_router_schema_adds_controls_without_mutating_registry():
    """Verify Router control fields are added on a deep copy of tool schemas."""

    tools = {"dieu_kien_ket_hon": _tool_schema("dieu_kien_ket_hon")}
    original = deepcopy(tools["dieu_kien_ket_hon"]["description"])

    schemas = _router_tool_descriptions(tools)
    properties = schemas[0]["function"]["parameters"]["properties"]

    assert "context_action" in properties
    assert "context_refs" in properties
    assert tools["dieu_kien_ket_hon"]["description"] == original


def test_function_args_keep_resolved_query_and_strip_controls():
    """Verify retrievers receive resolved query but no Router-only controls."""

    tools = {"dieu_kien_ket_hon": _tool_schema("dieu_kien_ket_hon")}
    call = {
        "name": "dieu_kien_ket_hon",
        "args": {
            "query": "Nữ 18 tuổi có đủ điều kiện kết hôn không?",
            "context_action": "reuse",
            "context_refs": ["ctx-1"],
            "time_scope": "current",
        },
    }

    function_args, resolved = _tool_function_args(
        tools,
        call,
        "Còn nữ thì sao?",
    )

    assert resolved == "Nữ 18 tuổi có đủ điều kiện kết hôn không?"
    assert function_args == {"query": resolved}


def test_policy_uses_resolved_follow_up_instead_of_raw_question():
    """Verify RetrieverPolicy evaluates the standalone follow-up query."""

    decision = _evaluate_tool_calls_policy(
        "Còn nữ thì sao?",
        [
            {
                "name": "dieu_kien_ket_hon",
                "args": {
                    "query": "Nữ 18 tuổi có đủ điều kiện kết hôn không?",
                    "context_action": "retrieve",
                    "time_scope": "current",
                },
            }
        ],
    )

    assert decision.final_tools == ["dieu_kien_ket_hon"]


def test_clarify_is_exclusive_when_router_also_selects_retriever():
    """Verify deterministic policy prevents retrieval beside clarification."""

    decision = _evaluate_tool_calls_policy(
        "Còn trường hợp đó thì sao?",
        [
            {
                "name": "clarify",
                "args": {"question": "Bạn đang hỏi về trường hợp nào?"},
            },
            {
                "name": "dieu_kien_ket_hon",
                "args": {
                    "query": "Điều kiện kết hôn trong trường hợp chưa xác định",
                    "context_action": "retrieve",
                    "time_scope": "current",
                },
            },
        ],
    )

    assert decision.final_tools == ["clarify"]
    assert "dieu_kien_ket_hon" in decision.rejected_tools


async def test_clarify_returns_direct_question_without_other_dependencies():
    """Verify clarification is a direct response with no external dependency."""

    question = "Bạn đang hỏi về căn nhà hay mảnh đất được tặng riêng?"

    result = await clarify_question(question)

    assert result == question
