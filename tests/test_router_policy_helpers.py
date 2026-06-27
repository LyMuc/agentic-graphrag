from __future__ import annotations

from application.router import (
    _strip_router_only_args,
    _with_router_confidence_schema,
)
from retriever_policy import policy_candidates_from_tool_calls


def _retriever_schema() -> dict:
    """Tạo schema retriever tối giản để test helper router.

    Returns:
        Dict schema dạng OpenAI function tool có tham số query bắt buộc.
    """
    return {
        "type": "function",
        "function": {
            "name": "cap_duong",
            "description": "Tra cứu cấp dưỡng.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                },
                "required": ["query"],
            },
        },
    }


def test_adds_optional_confidence_score_to_retriever_schema():
    schema = _retriever_schema()
    enriched = _with_router_confidence_schema(schema)

    properties = enriched["function"]["parameters"]["properties"]
    assert "confidence_score" in properties
    assert "confidence_score" not in enriched["function"]["parameters"]["required"]
    assert "confidence_score" not in schema["function"]["parameters"]["properties"]


def test_does_not_add_confidence_score_to_direct_tool_schema():
    schema = _retriever_schema()
    schema["function"]["name"] = "respond"

    enriched = _with_router_confidence_schema(schema)

    properties = enriched["function"]["parameters"]["properties"]
    assert "confidence_score" not in properties


def test_policy_candidates_parse_and_clamp_confidence_score():
    candidates = policy_candidates_from_tool_calls(
        [
            {"name": "cap_duong", "args": {"confidence_score": "1.5"}},
            {"name": "cap_duong", "args": {"confidence_score": 0.2}},
            {"name": "chia_tai_san_sau_ly_hon", "args": {"confidence_score": "bad"}},
        ]
    )

    assert [candidate.name for candidate in candidates] == [
        "cap_duong",
        "chia_tai_san_sau_ly_hon",
    ]
    assert candidates[0].confidence_score == 1.0
    assert candidates[1].confidence_score is None


def test_strip_router_only_args_before_runtime_call():
    args = _strip_router_only_args(
        {
            "query": "Có phải cấp dưỡng không?",
            "confidence_score": 0.81,
        }
    )

    assert args == {"query": "Có phải cấp dưỡng không?"}
