from __future__ import annotations

import asyncio
from copy import deepcopy
from typing import Any, Optional

from adapter.config import ROUTER_LLM, build_router_llm
from application.conversation_context import (
    context_refs_from_messages,
    current_kg_version,
    retrieval_memory_summary,
    validate_reuse_request,
)
from application.legal_context import process_context_strings
from application.retriever_catalog import DIRECT_TOOLS
from application.retriever_policy import PolicyDecision, evaluate_retriever_policy


_EXCLUSIVE_DIRECT_TOOLS = {"clarify", "respond"}


tool_picker_prompt = """
Bạn là một hệ thống định tuyến (Router Agent) thông minh.
Nhiệm vụ của bạn là đọc câu hỏi của người dùng và chọn ĐÚNG và ĐỦ các công cụ (tools) để giải quyết TOÀN BỘ câu hỏi.

QUY TẮC BẮT BUỘC (CRITICAL RULES):
1. PHÂN TÍCH NHIỀU Ý: Người dùng thường hỏi nhiều vấn đề trong cùng 1 câu. Bạn PHẢI bóc tách từng vế của câu hỏi và chọn công cụ tương ứng cho từng vế.
2. PHÂN TÍCH BỐI CẢNH PHÁP LÝ LIÊN QUAN: Ngay cả khi câu hỏi CHỈ có MỘT ý hỏi duy nhất, bạn vẫn PHẢI xác định TẤT CẢ các khía cạnh/bối cảnh pháp lý có liên quan để đảm bảo câu trả lời cuối cùng đầy đủ và chính xác. Một ý hỏi có thể cần nhiều công cụ khác nhau để cung cấp đủ căn cứ pháp lý:
   - Công cụ cho BỐI CẢNH/TIỀN ĐỀ pháp lý của câu hỏi (ví dụ: tình trạng hôn nhân, quan hệ pháp lý đang tồn tại).
   - Công cụ cho NỘI DUNG CHÍNH mà người dùng muốn biết (ví dụ: quyền, nghĩa vụ, hậu quả pháp lý).
3. KHÔNG gọi cùng 1 tool nhiều lần.
4. GIẢI THAM CHIẾU FOLLOW-UP: Với MỖI tool, tham số `query` phải là một câu hỏi ĐỘC LẬP, đầy đủ chủ thể, đối tượng, tình tiết và thời gian lấy từ lịch sử. Không để đại từ mơ hồ như "nó", "cái đó", "trường hợp trên" trong `query`.
5. TÁI SỬ DỤNG CONTEXT: Chỉ đặt `context_action="reuse"` khi BỘ NHỚ RETRIEVAL có `context_ref` của ĐÚNG retriever, cùng mốc thời gian và câu follow-up không mở thêm vấn đề pháp lý cần căn cứ mới. Nếu không chắc chắn, đặt `context_action="retrieve"`.
6. THỜI GIAN: Đặt `time_scope="current"` nếu người dùng hỏi luật hiện tại; `time_scope="explicit"` và điền `target_date` nếu có mốc cụ thể; `time_scope="ambiguous"` nếu mốc thời gian không thể xác định.
7. HỎI LÀM RÕ: Chỉ dùng `clarify` khi lịch sử gần và chỉ mục lượt cũ vẫn dẫn đến từ hai cách hiểu hợp lý trở lên. Không dùng `clarify` chỉ vì thiếu tình tiết mà có thể trả lời theo các trường hợp.
8. KHÔNG gọi cùng 1 tool nhiều lần.
9. `clarify` và `respond` là phản hồi trực tiếp: nếu chọn một trong hai thì KHÔNG chọn thêm retriever khác.

Ví dụ tư duy:

Ví dụ 1 (NHIỀU Ý HỎI):
- Câu hỏi: "Tôi là nam năm nay 18 tuổi thì có được kết hôn không? Và tôi có quyền được yêu cầu hủy kết hôn trái pháp luật của bố mẹ tôi không?"
- Ý 1: Hỏi về độ tuổi kết hôn (Nam 18 tuổi) -> Dùng công cụ `dieu_kien_ket_hon`
- Ý 2: Hỏi về quyền yêu cầu hủy kết hôn trái pháp luật -> Dùng công cụ `ket_hon_trai_phap_luat`
=> BẠN PHẢI GỌI CẢ 2 CÔNG CỤ NÀY.

Ví dụ 2 (MỘT Ý HỎI nhưng CẦN NHIỀU BỐI CẢNH PHÁP LÝ):
- Câu hỏi: "Không đăng ký kết hôn người cha có nghĩa vụ cấp dưỡng cho con không?"
- Bối cảnh pháp lý: "Không đăng ký kết hôn" -> liên quan đến quy định về chung sống như vợ chồng -> Dùng công cụ `chung_song_nhu_vo_chong`
- Nội dung chính: "nghĩa vụ cấp dưỡng cho con" -> Dùng công cụ `cap_duong`
=> BẠN PHẢI GỌI CẢ 2 CÔNG CỤ NÀY để có đầy đủ căn cứ pháp lý cho câu trả lời.

Ví dụ 3 (MỘT Ý HỎI nhưng CẦN NHIỀU BỐI CẢNH PHÁP LÝ):
- Câu hỏi: "Vợ có được chia nhà đất mà chỉ chồng đứng tên khi ly hôn không?"
- Bối cảnh pháp lý: Cần xác định việc chỉ một người đứng tên có làm nhà đất là tài sản riêng hay vẫn là tài sản chung -> Dùng công cụ `che_do_tai_san_cua_vo_chong`.
- Nội dung chính: Hỏi tài sản đó có được chia và chia thế nào khi ly hôn -> Dùng công cụ `chia_tai_san_sau_ly_hon`.
=> THƯỜNG PHẢI GỌI CẢ 2 CÔNG CỤ. Cách chọn này đặc biệt phù hợp khi câu hỏi có tình tiết về thời điểm tạo lập tài sản, nguồn tiền, người đứng tên, tặng cho hoặc thừa kế. Tuy nhiên, không phải mọi câu hỏi chia tài sản sau ly hôn đều bắt buộc gọi công cụ chế độ tài sản; nếu tính chất tài sản đã rõ và câu hỏi chỉ hỏi trực tiếp quy tắc chia thì có thể chỉ gọi `chia_tai_san_sau_ly_hon`.

Ví dụ 4 (MỘT Ý HỎI nhưng CẦN NHIỀU BỐI CẢNH PHÁP LÝ):
- Câu hỏi: "Trong thời kỳ hôn nhân chồng tôi vay tiền làm ăn; sau ly hôn tôi có phải cùng trả khoản nợ đó không?"
- Bối cảnh pháp lý: Cần xác định khoản nợ/nghĩa vụ là chung hay riêng của vợ chồng và người vợ có trách nhiệm liên đới phải trả nợ hay không -> Dùng 2 công cụ `che_do_tai_san_cua_vo_chong` và `dai_dien_trach_nhiem_vo_chong`.
- Nội dung chính: Hỏi người vợ SAU LY HÔN có vẫn phải chịu nghĩa vụ trả nợ hay không -> Dùng công cụ `chia_tai_san_sau_ly_hon`.
=> THƯỜNG PHẢI GỌI CẢ 3 CÔNG CỤ NÀY.
"""


def _tool_accepts_query(tools: dict[str, Any], tool_name: str) -> bool:
    """Check whether a registered tool schema declares a ``query`` argument.

    Args:
        tools: Runtime tool registry.
        tool_name: Registered tool name.

    Returns:
        ``True`` when the tool function schema exposes ``query``.
    """

    properties = (
        tools[tool_name]["description"]
        .get("function", {})
        .get("parameters", {})
        .get("properties", {})
    )
    return "query" in properties


def _tool_call_name(tool_call: dict[str, Any]) -> str:
    """Extract a normalized tool name from a Router call.

    Args:
        tool_call: Router tool-call dictionary.

    Returns:
        Tool name as a string, or an empty string when absent.
    """

    return str(tool_call.get("name", ""))


def _unique_tool_calls(tool_calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove duplicate Router calls while preserving first-tool order.

    Args:
        tool_calls: Raw Router tool calls.

    Returns:
        Calls with at most one entry per non-empty tool name.
    """

    seen_tools: set[str] = set()
    unique_tool_calls: list[dict[str, Any]] = []
    for tool_call in tool_calls:
        tool_name = _tool_call_name(tool_call)
        if not tool_name or tool_name in seen_tools:
            continue
        seen_tools.add(tool_name)
        unique_tool_calls.append(tool_call)
    return unique_tool_calls


def _build_policy_tool_calls(
    llm_tool_calls: list[dict[str, Any]],
    final_tools: list[str],
) -> list[dict[str, Any]]:
    """Build executable tool calls from policy output, giữ tên gốc từ router.

    Args:
        llm_tool_calls: Tool calls thô từ router LLM.
        final_tools: Danh sách tên sau policy filter.

    Returns:
        Tool calls khớp final_tools, giữ nguyên args gốc nếu có.
    """
    by_name: dict[str, dict[str, Any]] = {}
    for call in _unique_tool_calls(llm_tool_calls):
        name = _tool_call_name(call)
        by_name[name] = {**call, "name": name}

    out: list[dict[str, Any]] = []
    for tool_name in final_tools:
        out.append(by_name.get(tool_name, {"name": tool_name, "args": {}}))
    return out


def _validate_registered_tools(tools: dict[str, Any], tool_calls: list[dict[str, Any]]) -> None:
    """Ensure every policy-approved tool exists in the runtime registry.

    Args:
        tools: Runtime tool registry.
        tool_calls: Calls approved for execution.

    Returns:
        ``None`` when all tool names are registered.

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
            "RetrieverPolicy selected tool(s) that are not registered in tools: "
            f"{missing_list}. Register the corresponding retriever(s) before routing."
        )


def _router_tool_descriptions(tools: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Build Router schemas and add optional conversation-control arguments.

    Args:
        tools: Optional runtime registry. When supplied, only registered tools
            are exposed; otherwise the catalog registry is used.

    Returns:
        Deep-copied OpenAI tool schemas. Non-direct retrievers receive optional
        ``context_action``, ``context_refs``, ``time_scope``, and ``target_date``
        properties without mutating their original descriptions.
    """
    if tools:
        descriptions = [
            deepcopy(entry["description"])
            for entry in tools.values()
            if isinstance(entry, dict) and "description" in entry
        ]
    else:
        from application.router_tool_registry import router_tools_for_llm

        descriptions = deepcopy(router_tools_for_llm())

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
    return descriptions


_CONTROL_ARGS = {
    "context_action",
    "context_refs",
    "time_scope",
    "target_date",
}


def _resolved_query(tool_call: dict[str, Any], fallback_question: str) -> str:
    """Return the Router-resolved standalone query for one tool call.

    Args:
        tool_call: Router tool-call dictionary.
        fallback_question: Raw current question used when ``args.query`` is
            missing or blank.

    Returns:
        Non-empty standalone query string.
    """

    args = tool_call.get("args") or {}
    query = str(args.get("query") or "").strip()
    return query or fallback_question


def _tool_function_args(
    tools: dict[str, Any],
    tool_call: dict[str, Any],
    fallback_question: str,
) -> tuple[dict[str, Any], str]:
    """Build callable arguments without Router-only cache controls.

    Args:
        tools: Runtime tool registry used to detect ``query`` support.
        tool_call: Router call containing business and control arguments.
        fallback_question: Raw question used only when ``args.query`` is absent.

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


def _evaluate_tool_calls_policy(
    question: str,
    llm_tool_calls: list[dict[str, Any]],
) -> PolicyDecision:
    """Apply RetrieverPolicy independently to each resolved tool query.

    Args:
        question: Raw current user question for top-level audit metadata.
        llm_tool_calls: Router tool calls containing per-tool resolved queries.

    Returns:
        Combined ``PolicyDecision``. Direct tools are retained unchanged while
        each retriever is filtered against its own standalone ``args.query``.
    """

    unique_calls = _unique_tool_calls(llm_tool_calls)
    candidates = [_tool_call_name(call) for call in unique_calls]
    exclusive_call = next(
        (
            call
            for call in unique_calls
            if _tool_call_name(call) in _EXCLUSIVE_DIRECT_TOOLS
        ),
        None,
    )
    if exclusive_call is not None:
        exclusive_name = _tool_call_name(exclusive_call)
        rejected_tools = {
            name: f"{exclusive_name} is an exclusive direct-response tool."
            for name in candidates
            if name != exclusive_name
        }
        return PolicyDecision(
            question=question,
            prepared_question="",
            llm_candidates=candidates,
            final_tools=[exclusive_name],
            rejected_tools=rejected_tools,
            audit=[
                "LLM candidates: "
                + (", ".join(candidates) if candidates else "(none)"),
                f"Final retrievers: {exclusive_name}",
                (
                    f"{exclusive_name}: kept exclusively; retrievers and other "
                    "direct tools were skipped."
                ),
            ],
        )

    final_tools: list[str] = []
    rejected_tools: dict[str, str] = {}
    audit = [
        "LLM candidates: " + (", ".join(candidates) if candidates else "(none)")
    ]
    prepared_parts: list[str] = []
    for call in unique_calls:
        name = _tool_call_name(call)
        resolved = _resolved_query(call, question)
        if name in DIRECT_TOOLS:
            final_tools.append(name)
            audit.append(f"{name}: direct tool kept.")
            continue
        decision = evaluate_retriever_policy(resolved, [name])
        prepared_parts.append(decision.prepared_question)
        if name in decision.final_tools:
            final_tools.append(name)
            audit.append(f"{name}: kept for resolved query '{resolved}'.")
        else:
            reason = decision.rejected_tools.get(name, "RetrieverPolicy rejected.")
            rejected_tools[name] = reason
            audit.append(f"{name}: rejected for resolved query '{resolved}' ({reason})")
    audit.insert(
        1,
        "Final retrievers: " + (", ".join(final_tools) if final_tools else "(none)"),
    )
    return PolicyDecision(
        question=question,
        prepared_question=" | ".join(prepared_parts),
        llm_candidates=candidates,
        final_tools=final_tools,
        rejected_tools=rejected_tools,
        audit=audit,
    )


async def _execute_tool_call(
    tools: dict[str, Any],
    tool_call: dict[str, Any],
    updated_question: str,
    *,
    cache_fallback_reason: str = "",
) -> Any:
    """Execute one registered tool and expose a readable Chainlit trace.

    Args:
        tools: Tool registry mapping names to descriptions and async callables.
        tool_call: Router-produced tool call with ``name`` and ``args``.
        updated_question: Fallback query used when the tool call omitted one.
        cache_fallback_reason: Optional deterministic reason why a requested
            cache reuse was rejected and retrieval was executed instead.

    Returns:
        Raw tool result. Dictionary results are annotated with
        ``retriever_name``. Encoded LegalContextBundles are rendered only for
        the UI step; the returned result remains structured for later merging.

    Raises:
        RuntimeError: If the selected tool is not registered.
    """
    import chainlit as cl

    tool_name = _tool_call_name(tool_call)
    if tool_name not in tools:
        raise RuntimeError(
            f"Tool '{tool_name}' is not registered. Register the retriever in tools."
        )

    async with cl.Step(name=f"Retriever: {tool_name}") as step:
        function_to_call = tools[tool_name]["function"]
        function_args, resolved_query = _tool_function_args(
            tools,
            tool_call,
            updated_question,
        )

        step.input = f"Tool Input: {function_args}"
        res = await function_to_call(**function_args)
        if isinstance(res, dict):
            res["retriever_name"] = tool_name
            res["resolved_query"] = resolved_query
            res["cache_status"] = "retrieved"
            if cache_fallback_reason:
                res["cache_fallback_reason"] = cache_fallback_reason
        if isinstance(res, dict) and "contexts" in res:
            debug = (res.get("debug") or "").strip()
            if debug:
                step.output = debug
            else:
                pipeline = process_context_strings(res["contexts"])
                step.output = pipeline.rendered_text or "Khong tim thay context phu hop."
        elif isinstance(res, list):
            parts = [str(item) for item in res if item is not None]
            step.output = (
                "\n\n".join(parts)
                if parts
                else "Khong tim thay context phu hop."
            )
        else:
            step.output = str(res)
        step.metadata = {"raw_result": res}
        return res


async def _reuse_tool_call(
    tool_call: dict[str, Any],
    validation_contexts: list[str],
    context_refs: list[str],
    updated_question: str,
) -> dict[str, Any]:
    """Return validated cached contexts through a visible Chainlit retriever step.

    Args:
        tool_call: Router call requesting ``context_action="reuse"``.
        validation_contexts: Encoded bundles accepted by deterministic checks.
        context_refs: Validated retrieval-memory references.
        updated_question: Raw question used only as a resolved-query fallback.

    Returns:
        Retriever-like dictionary compatible with the normal response pipeline,
        annotated with ``cache_status="reused"`` and used context references.
    """

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
        step.output = result["debug"]
        step.metadata = {"raw_result": result}
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
    """Reuse validated context or execute the selected tool as a fallback.

    Args:
        tools: Runtime tool registry.
        tool_call: Policy-approved Router tool call.
        updated_question: Raw current question used as query fallback.
        retrieval_memory: Active thread's context cache.
        thread_id: Active Chainlit thread identifier.
        kg_version: Current knowledge-graph version.

    Returns:
        Cached retriever-like result when validation succeeds; otherwise the
        normal tool result. Direct tools always execute normally.
    """

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

    Args:
        tools: Runtime tool registry.
        tool_calls: Policy-approved Router calls.
        updated_question: Raw current question used as query fallback.
        retrieval_memory: Optional active-thread cache mapping.
        thread_id: Active thread ID used to prevent cross-thread reuse.
        kg_version: Current KG version; defaults to ``current_kg_version()``.

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


def llm_candidate_names(tool_calls: list[dict[str, Any]]) -> list[str]:
    """Tên retriever gốc từ router tool_calls (trước RetrieverPolicy).

    Args:
        tool_calls: Tool calls thô từ router LLM.

    Returns:
        Danh sách tên retriever không trùng, bỏ direct tools.
    """
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
    """Ask the Router LLM for raw retriever candidates only.

    Args:
        question: Standalone question to route.
        tools_for_llm: Optional explicit OpenAI tool schemas.

    Returns:
        Raw Router tool calls without policy filtering or execution.
    """
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
        tools=tools_for_llm,
    )


async def tool_choice(
    messages: list[dict[str, str]],
    temperature: float = 0,
    tools: Optional[list[dict[str, Any]]] = None,
    config: Optional[dict[str, Any]] = None,
    model: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Invoke the configured Router LLM with tool calling enabled.

    Args:
        messages: Router prompt and bounded conversation history.
        temperature: Compatibility argument; Router remains deterministic.
        tools: OpenAI-compatible tool schemas.
        config: Optional LangChain invocation config kept for compatibility.
        model: Compatibility argument; configured ``ROUTER_LLM`` is used.

    Returns:
        Raw tool-call dictionaries returned by the Router model.
    """

    # temperature/config/model are kept for compatibility with existing scripts.
    _ = (temperature, config, model)
    llm = build_router_llm()
    llm_with_tools = llm.bind_tools(tools or [], tool_choice="any")
    res = await llm_with_tools.ainvoke(messages)
    if not res.tool_calls:
        print(f"[Router] No tool_calls returned. model={ROUTER_LLM} content={res.content}")
    return res.tool_calls


async def route_question_with_audit(
    question: str,
    tools: dict[str, Any],
    answers: list[dict[str, str]],
    *,
    retrieval_memory: dict[str, dict[str, Any]] | None = None,
    thread_id: str = "",
    kg_version: str | None = None,
) -> tuple[list[Any], PolicyDecision]:
    """Route one question, filter each resolved query, and execute or reuse tools.

    Args:
        question: Raw current user question.
        tools: Runtime tool registry.
        answers: Token-bounded working history, including optional old anchors.
        retrieval_memory: Active thread's cached LegalContextBundles.
        thread_id: Active Chainlit thread ID.
        kg_version: Current KG version used by deterministic cache validation.

    Returns:
        Tuple of tool results and a combined auditable policy decision.
    """

    memory = retrieval_memory or {}
    llm_tool_calls = await tool_choice(
        [
            {
                "role": "system",
                "content": tool_picker_prompt,
            },
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
        ],
        tools=_router_tool_descriptions(tools),
    )

    policy_decision = _evaluate_tool_calls_policy(question, llm_tool_calls)
    policy_tool_calls = _build_policy_tool_calls(
        llm_tool_calls,
        policy_decision.final_tools,
    )
    tool_response = await handle_tool_calls(
        tools,
        policy_tool_calls,
        question,
        retrieval_memory=memory,
        thread_id=thread_id,
        kg_version=kg_version or current_kg_version(),
    )
    return tool_response, policy_decision


async def route_question(
    question: str,
    tools: dict[str, Any],
    answers: list[dict[str, str]],
) -> list[Any]:
    """Compatibility wrapper returning only tool results for one question.

    Args:
        question: Raw or standalone user question.
        tools: Runtime tool registry.
        answers: Working conversation history.

    Returns:
        Tool execution results; policy audit information is discarded.
    """

    tool_response, _ = await route_question_with_audit(question, tools, answers)
    return tool_response
