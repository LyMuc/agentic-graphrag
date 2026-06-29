"""RouterAgent (top-level) — chọn tool bằng LLM rồi fan-out song song.

Tách từ ``application/router.py`` trong Phase 4 refactor. RouterAgent là thin
wrapper kế thừa ``Agent``: ``decide`` (LLM tool-pick) + ``dispatch`` (thực thi
song song) ủy quyền cho các hàm module đã kiểm chứng.
"""
from __future__ import annotations

from typing import Any, Optional

from server.agents.base import Agent
from server.infrastructure.llm.factory import ROUTER_LLM, build_router_llm
from server.conversation.history import context_refs_from_messages
from server.conversation.memory import current_kg_version, retrieval_memory_summary
from server.agents.router.catalog import DIRECT_TOOLS
from server.agents.router.prompt import tool_picker_prompt
from server.agents.router.reuse import handle_tool_calls
from server.agents.router.schema import (
    _router_tool_descriptions,
    _tool_call_name,
    _unique_tool_calls,
    _with_router_confidence_schema,
)


def _route_messages(
    question: str,
    answers: list[dict[str, str]],
    memory: dict[str, dict[str, Any]],
) -> list[dict[str, str]]:
    """Build the Router LLM message list (prompt + history + memory + question)."""

    return [
        {"role": "system", "content": tool_picker_prompt},
        *answers,
        {
            "role": "system",
            "content": (
                "BỘ NHỚ RETRIEVAL KHẢ DỤNG:\n"
                f"{retrieval_memory_summary(memory, preferred_refs=context_refs_from_messages(answers))}"
            ),
        },
        {
            "role": "user",
            "content": (
                "Cau hoi cua nguoi dung can tim cong cu de giai quyet: "
                f"'{question}'"
            ),
        },
    ]


async def tool_choice(
    messages: list[dict[str, str]],
    temperature: float = 0,
    tools: Optional[list[dict[str, Any]]] = None,
    config: Optional[dict[str, Any]] = None,
    model: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Invoke the configured Router LLM with tool calling enabled.

    Returns:
        Raw tool-call dictionaries returned by the Router model.
    """

    # temperature/config/model are kept for compatibility with existing scripts.
    _ = (temperature, config, model)
    llm = build_router_llm()
    bound_tools = [_with_router_confidence_schema(tool) for tool in (tools or [])]
    llm_with_tools = llm.bind_tools(bound_tools, tool_choice="any")
    res = await llm_with_tools.ainvoke(messages)
    if not res.tool_calls:
        print(f"[Router] No tool_calls returned. model={ROUTER_LLM} content={res.content}")
    return res.tool_calls


def llm_candidate_names(tool_calls: list[dict[str, Any]]) -> list[str]:
    """Tên retriever gốc từ router tool_calls (trước RetrieverPolicy)."""
    seen: set[str] = set()
    out: list[str] = []
    for call in _unique_tool_calls(tool_calls):
        name = _tool_call_name(call)
        if name in DIRECT_TOOLS:
            continue
        if name in seen:
            continue
        seen.add(name)
        out.append(name)
    return out


async def llm_retriever_candidates(
    question: str,
    *,
    tools_for_llm: Optional[list[dict[str, Any]]] = None,
) -> list[dict[str, Any]]:
    """Ask the Router LLM for raw retriever candidates only."""
    bound_tools = (
        [_with_router_confidence_schema(tool) for tool in tools_for_llm]
        if tools_for_llm is not None
        else None
    )
    return await tool_choice(
        [
            {"role": "system", "content": tool_picker_prompt},
            {
                "role": "user",
                "content": (
                    "Cau hoi cua nguoi dung can tim cong cu de giai quyet: "
                    f"'{question}'"
                ),
            },
        ],
        tools=bound_tools,
    )


async def route_question_with_audit(
    question: str,
    tools: dict[str, Any],
    answers: list[dict[str, str]],
    *,
    retrieval_memory: dict[str, dict[str, Any]] | None = None,
    thread_id: str = "",
    kg_version: str | None = None,
) -> tuple[list[Any], None]:
    """Route one question and execute or reuse router-selected tools.

    Returns:
        Tuple of tool results and ``None`` (policy audit slot kept for API compat).
    """

    memory = retrieval_memory or {}
    llm_tool_calls = await tool_choice(
        _route_messages(question, answers, memory),
        tools=_router_tool_descriptions(tools),
    )

    tool_calls = _unique_tool_calls(llm_tool_calls)
    tool_response = await handle_tool_calls(
        tools,
        tool_calls,
        question,
        retrieval_memory=memory,
        thread_id=thread_id,
        kg_version=kg_version or current_kg_version(),
    )
    return tool_response, None


async def route_question(
    question: str,
    tools: dict[str, Any],
    answers: list[dict[str, str]],
) -> list[Any]:
    """Compatibility wrapper returning only tool results for one question."""

    tool_response, _ = await route_question_with_audit(question, tools, answers)
    return tool_response


class RouterAgent(Agent):
    """Top-level Router (stateless) áp dụng pattern routing.

    ``decide`` chọn tool bằng Router LLM, ``dispatch`` fan-out song song với cache
    reuse xác định. ``run`` ghép cả hai (tương đương ``route_question_with_audit``).
    """

    name = "router"

    def __init__(self, *, tools: dict[str, Any] | None = None):
        self.tool_picker_prompt = tool_picker_prompt
        self._tools = tools or {}

    async def decide(
        self,
        question: str,
        answers: list[dict[str, str]],
        *,
        retrieval_memory: dict[str, dict[str, Any]] | None = None,
        tools: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """LLM tool-pick → danh sách tool call không trùng."""
        memory = retrieval_memory or {}
        registry = tools if tools is not None else self._tools
        llm_tool_calls = await tool_choice(
            _route_messages(question, answers, memory),
            tools=_router_tool_descriptions(registry),
        )
        return _unique_tool_calls(llm_tool_calls)

    async def dispatch(
        self,
        tools: dict[str, Any],
        tool_calls: list[dict[str, Any]],
        question: str,
        *,
        retrieval_memory: dict[str, dict[str, Any]] | None = None,
        thread_id: str = "",
        kg_version: str | None = None,
    ) -> list[Any]:
        """Fan-out song song các tool call (execute / reuse cache)."""
        return await handle_tool_calls(
            tools,
            tool_calls,
            question,
            retrieval_memory=retrieval_memory,
            thread_id=thread_id,
            kg_version=kg_version,
        )

    async def run(
        self,
        question: str,
        tools: dict[str, Any],
        answers: list[dict[str, str]],
        *,
        retrieval_memory: dict[str, dict[str, Any]] | None = None,
        thread_id: str = "",
        kg_version: str | None = None,
    ) -> tuple[list[Any], None]:
        """Decide + dispatch trong một lượt (giữ chữ ký route_question_with_audit)."""
        return await route_question_with_audit(
            question,
            tools,
            answers,
            retrieval_memory=retrieval_memory,
            thread_id=thread_id,
            kg_version=kg_version,
        )
