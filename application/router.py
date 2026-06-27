from __future__ import annotations

import asyncio
from copy import deepcopy
from typing import Any, Iterable, Optional

from adapter.config import ROUTER_LLM, build_router_llm
from application.conversation_context import (
    context_refs_from_messages,
    current_kg_version,
    retrieval_memory_summary,
    validate_reuse_request,
)
from application.legal_context import process_context_strings
from application.retriever_catalog import DIRECT_TOOLS


ROUTER_ONLY_ARGS = {"confidence_score"}


def _render_retriever_contexts_for_ui(contexts: Iterable[Any]) -> str:
    """Render encoded bundles / legacy context strings for Chainlit retriever steps."""

    pipeline = process_context_strings(contexts)
    return pipeline.rendered_text or "Khong tim thay context phu hop."


RETRIEVER_QUERY_PARAM_DESCRIPTION = (
    "Câu hỏi của người dùng. MẶC ĐỊNH copy NGUYÊN VĂN toàn bộ câu hỏi user "
    "vừa nhập trong lượt hiện tại. Chỉ được thay đại từ tham chiếu "
    "(anh ấy, cô ấy, họ, nó, cái đó, trường hợp đó, vậy, như vậy, vậy thì, "
    "thế thì) hoặc ellipsis follow-up (ví dụ 'Còn X thì sao?') bằng chủ thể "
    "tương ứng từ lịch sử khi câu hỏi là follow-up. KHÔNG paraphrase, KHÔNG "
    "tóm tắt, KHÔNG tách thành sub-question, KHÔNG bỏ chi tiết tình huống. "
    "Khi gọi nhiều retriever trong cùng lượt, mọi retriever nhận query GIỐNG "
    "HỆT NHAU."
)


tool_picker_prompt = """
Bạn là một hệ thống định tuyến (Router Agent) thông minh.
Nhiệm vụ của bạn là đọc câu hỏi của người dùng và chọn ĐÚNG và ĐỦ các công cụ (tools) để giải quyết TOÀN BỘ câu hỏi.

QUY TẮC BẮT BUỘC (CRITICAL RULES):
1. PHÂN TÍCH NHIỀU Ý: Người dùng thường hỏi nhiều vấn đề trong cùng 1 câu. Bạn PHẢI bóc tách từng vế của câu hỏi và chọn công cụ tương ứng cho từng vế.
2. PHÂN TÍCH BỐI CẢNH PHÁP LÝ LIÊN QUAN: Ngay cả khi câu hỏi CHỈ có MỘT ý hỏi duy nhất, bạn vẫn PHẢI xác định TẤT CẢ các khía cạnh/bối cảnh pháp lý có liên quan để đảm bảo câu trả lời cuối cùng đầy đủ và chính xác. Một ý hỏi có thể cần nhiều công cụ khác nhau để cung cấp đủ căn cứ pháp lý:
   - Công cụ cho BỐI CẢNH/TIỀN ĐỀ pháp lý của câu hỏi (ví dụ: tình trạng hôn nhân, quan hệ pháp lý đang tồn tại).
   - Công cụ cho NỘI DUNG CHÍNH mà người dùng muốn biết (ví dụ: quyền, nghĩa vụ, hậu quả pháp lý).
3. KHÔNG gọi cùng 1 tool nhiều lần.
4. THAM SỐ `query` — GIỮ NGUYÊN VĂN, CHỈ RESOLVE PRONOUN KHI FOLLOW-UP:
   - MẶC ĐỊNH: tham số `query` cho MỌI tool được chọn PHẢI là TOÀN BỘ câu hỏi gốc của user trong lượt hiện tại, copy nguyên văn. Không paraphrase, không tóm tắt, không bỏ chi tiết, không tách thành sub-question.
   - CHỈ SỬA KHI FOLLOW-UP CÓ PRONOUN/ANAPHORA: nếu câu hỏi hiện tại chứa đại từ tham chiếu (anh ấy, cô ấy, họ, nó, cái đó, trường hợp đó, vậy, như vậy, vậy thì, thế thì) HOẶC ellipsis kiểu "Còn X thì sao?", chỉ được thay phần đại từ/ellipsis đó bằng cụm danh từ tương ứng từ lịch sử gần. Giữ nguyên phần còn lại của câu.
   - CẤM: tóm tắt nhiều vế thành một vế; chia một câu thành nhiều query khác nhau cho các retriever; thêm tình tiết LLM tự suy ra; bỏ kịch bản tình huống user mô tả.
   - NHIỀU RETRIEVER → CÙNG MỘT `query`: khi gọi nhiều retriever cho cùng một lượt, tất cả nhận `query` GIỐNG HỆT NHAU. Phân biệt retriever bằng `name`, không bằng cách viết query khác nhau.
5. TÁI SỬ DỤNG CONTEXT: Chỉ đặt `context_action="reuse"` khi BỘ NHỚ RETRIEVAL có `context_ref` của ĐÚNG retriever, cùng mốc thời gian và câu follow-up không mở thêm vấn đề pháp lý cần căn cứ mới. Nếu không chắc chắn, đặt `context_action="retrieve"`.
6. THỜI GIAN: Đặt `time_scope="current"` nếu người dùng hỏi luật hiện tại; `time_scope="explicit"` và điền `target_date` nếu có mốc cụ thể; `time_scope="ambiguous"` nếu mốc thời gian không thể xác định.
7. HỎI LÀM RÕ: Chỉ dùng `clarify` khi lịch sử gần và chỉ mục lượt cũ vẫn dẫn đến từ hai cách hiểu hợp lý trở lên. Không dùng `clarify` chỉ vì thiếu tình tiết mà có thể trả lời theo các trường hợp.
8. ĐIỂM TỰ TIN: Với mỗi tool retriever được gọi, điền thêm `confidence_score` là một số từ 0.0 đến 1.0 thể hiện mức chắc chắn tool đó cần thiết để trả lời câu hỏi. Đây chỉ là metadata định tuyến, không phải nội dung pháp lý.
9. `clarify` và `respond` là phản hồi trực tiếp: nếu chọn một trong hai thì KHÔNG chọn thêm retriever khác.

Ví dụ tư duy:

Ví dụ 1 (NHIỀU Ý HỎI — chọn nhiều tool, query NGUYÊN VĂN):
- Câu hỏi: "Tôi là nam năm nay 18 tuổi thì có được kết hôn không? Và tôi có quyền được yêu cầu hủy kết hôn trái pháp luật của bố mẹ tôi không?"
- Tool: `dieu_kien_ket_hon`, `ket_hon_trai_phap_luat`
- `query` cho CẢ HAI tool = nguyên văn toàn bộ câu hỏi trên. KHÔNG tách, KHÔNG tóm tắt.

Ví dụ 2 (MỘT Ý HỎI, NHIỀU BỐI CẢNH PHÁP LÝ — query NGUYÊN VĂN):
- Câu hỏi: "Không đăng ký kết hôn người cha có nghĩa vụ cấp dưỡng cho con không?"
- Tool: `chung_song_nhu_vo_chong`, `cap_duong`
- `query` cho CẢ HAI tool = nguyên văn toàn bộ câu hỏi trên.

Ví dụ 3 (MỘT Ý HỎI, NHIỀU BỐI CẢNH PHÁP LÝ — query NGUYÊN VĂN):
- Câu hỏi: "Vợ có được chia nhà đất mà chỉ chồng đứng tên khi ly hôn không?"
- Tool: thường `che_do_tai_san_cua_vo_chong` và `chia_tai_san_sau_ly_hon` (hoặc chỉ `chia_tai_san_sau_ly_hon` nếu tính chất tài sản đã rõ)
- `query` cho mọi tool được chọn = nguyên văn toàn bộ câu hỏi trên.

Ví dụ 4 (MỘT Ý HỎI, NHIỀU BỐI CẢNH PHÁP LÝ — query NGUYÊN VĂN):
- Câu hỏi: "Trong thời kỳ hôn nhân chồng tôi vay tiền làm ăn; sau ly hôn tôi có phải cùng trả khoản nợ đó không?"
- Tool: thường `che_do_tai_san_cua_vo_chong`, `dai_dien_trach_nhiem_vo_chong`, `chia_tai_san_sau_ly_hon`
- `query` cho mọi tool được chọn = nguyên văn toàn bộ câu hỏi trên.

Ví dụ 5 (CÂU DÀI CÓ KỊCH BẢN — query NGUYÊN VĂN, KHÔNG TÓM TẮT):
- Câu hỏi: "Sau khi kết hôn, anh Thắng yêu cầu vợ là chị Huyền ở nhà nội trợ, chăm sóc con nhỏ và bố mẹ chồng già yếu. ... Hỏi: ý kiến mẹ chồng tài sản là của anh Thắng đúng/sai? Tài sản vợ chồng anh Thắng và chị Huyền được pháp luật quy định thế nào?"
- Tool: `che_do_tai_san_cua_vo_chong`, `quyen_nghia_vu_vo_chong`
- `query` cho CẢ HAI tool = nguyên văn TOÀN BỘ đoạn câu hỏi (kể cả kịch bản tình huống). KHÔNG tách thành sub-question theo từng retriever.

Ví dụ 6 (FOLLOW-UP CÓ PRONOUN/ELLIPSIS — CHỈ RESOLVE PHẦN THAM CHIẾU):
- Lượt trước: "Nam 18 tuổi có được kết hôn không?"
- Lượt hiện tại: "Còn nữ thì sao?"
- Tool: `dieu_kien_ket_hon`
- `query` = "Nữ 18 tuổi có được kết hôn không?" (chỉ thay ellipsis "Còn nữ thì sao?" bằng câu hỏi tương đương đầy đủ, không thêm/bớt tình tiết).
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


def _tool_schema_name(schema: dict[str, Any]) -> str:
    """Lấy tên function tool từ schema truyền cho Router LLM.

    Args:
        schema: OpenAI/LangChain tool schema dạng dict.

    Returns:
        Tên function trong schema, hoặc chuỗi rỗng nếu schema thiếu/không hợp lệ.
    """
    return str(schema.get("function", {}).get("name", ""))


def _with_router_confidence_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Thêm optional confidence_score vào schema retriever gửi cho Router LLM.

    Args:
        schema: Tool schema gốc từ retriever hoặc direct tool.

    Returns:
        Bản copy của schema. Với retriever known, bản copy có thêm property
        confidence_score trong parameters; direct tool hoặc schema không hợp lệ
        được trả về dưới dạng copy không đổi.
    """
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
    """Loại metadata chỉ dùng cho router trước khi gọi function thật.

    Args:
        args: Dict tham số lấy từ tool call của Router LLM.

    Returns:
        Dict mới không chứa các khóa router-only như confidence_score.
    """
    return {key: value for key, value in args.items() if key not in ROUTER_ONLY_ARGS}


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


def _validate_registered_tools(tools: dict[str, Any], tool_calls: list[dict[str, Any]]) -> None:
    """Ensure every router-selected tool exists in the runtime registry.

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
        from application.router_tool_registry import router_tools_for_llm

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


async def _execute_tool_call(
    tools: dict[str, Any],
    tool_call: dict[str, Any],
    updated_question: str,
    *,
    cache_fallback_reason: str = "",
) -> Any:
    """Execute one registered tool and optionally expose a Chainlit trace.

    Args:
        tools: Tool registry mapping names to descriptions and async callables.
        tool_call: Router-produced tool call with ``name`` and ``args``.
        updated_question: Fallback query used when the tool call omitted one.
        cache_fallback_reason: Optional deterministic reason why a requested
            cache reuse was rejected and retrieval was executed instead.

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
    bound_tools = [_with_router_confidence_schema(tool) for tool in (tools or [])]
    llm_with_tools = llm.bind_tools(bound_tools, tool_choice="any")
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
) -> tuple[list[Any], None]:
    """Route one question and execute or reuse router-selected tools.

    Args:
        question: Raw current user question.
        tools: Runtime tool registry.
        answers: Token-bounded working history, including optional old anchors.
        retrieval_memory: Active thread's cached LegalContextBundles.
        thread_id: Active Chainlit thread ID.
        kg_version: Current KG version used by deterministic cache validation.

    Returns:
        Tuple of tool results and ``None`` (policy audit slot kept for API compat).
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
    """Compatibility wrapper returning only tool results for one question.

    Args:
        question: Raw or standalone user question.
        tools: Runtime tool registry.
        answers: Working conversation history.

    Returns:
        Tool execution results; policy audit slot is always ``None``.
    """

    tool_response, _ = await route_question_with_audit(question, tools, answers)
    return tool_response
