from __future__ import annotations

import asyncio
import copy
from typing import Any, Optional

from adapter.config import ROUTER_LLM, build_router_llm
from application.retriever_catalog import DIRECT_TOOLS
from application.retriever_policy import (
    PolicyCandidate,
    PolicyDecision,
    evaluate_retriever_policy,
)


ROUTER_ONLY_ARGS = {"confidence_score"}


tool_picker_prompt = """
Bạn là một hệ thống định tuyến (Router Agent) thông minh.
Nhiệm vụ của bạn là đọc câu hỏi của người dùng và chọn ĐÚNG và ĐỦ các công cụ (tools) để giải quyết TOÀN BỘ câu hỏi.

QUY TẮC BẮT BUỘC (CRITICAL RULES):
1. PHÂN TÍCH NHIỀU Ý: Người dùng thường hỏi nhiều vấn đề trong cùng 1 câu. Bạn PHẢI bóc tách từng vế của câu hỏi và chọn công cụ tương ứng cho từng vế.
2. PHÂN TÍCH BỐI CẢNH PHÁP LÝ LIÊN QUAN: Ngay cả khi câu hỏi CHỈ có MỘT ý hỏi duy nhất, bạn vẫn PHẢI xác định TẤT CẢ các khía cạnh/bối cảnh pháp lý có liên quan để đảm bảo câu trả lời cuối cùng đầy đủ và chính xác. Một ý hỏi có thể cần nhiều công cụ khác nhau để cung cấp đủ căn cứ pháp lý:
   - Công cụ cho BỐI CẢNH/TIỀN ĐỀ pháp lý của câu hỏi (ví dụ: tình trạng hôn nhân, quan hệ pháp lý đang tồn tại).
   - Công cụ cho NỘI DUNG CHÍNH mà người dùng muốn biết (ví dụ: quyền, nghĩa vụ, hậu quả pháp lý).
3. KHÔNG gọi cùng 1 tool nhiều lần.
4. ĐIỀN ĐỦ THAM SỐ: Đảm bảo tham số `query` chứa nguyên văn ý hỏi của người dùng cho công cụ đó.
5. ĐIỂM TỰ TIN: Với mỗi tool retriever được gọi, điền thêm `confidence_score` là một số từ 0.0 đến 1.0 thể hiện mức chắc chắn tool đó cần thiết để trả lời câu hỏi. Đây chỉ là metadata định tuyến, không phải nội dung pháp lý.

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
    properties = (
        tools[tool_name]["description"]
        .get("function", {})
        .get("parameters", {})
        .get("properties", {})
    )
    return "query" in properties


def _tool_call_name(tool_call: dict[str, Any]) -> str:
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
    out = copy.deepcopy(schema)
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


def _coerce_confidence_score(value: Any) -> float | None:
    """Chuẩn hóa confidence_score trong tool call args về khoảng 0.0-1.0.

    Args:
        value: Giá trị thô do Router LLM trả về.

    Returns:
        Float đã clamp trong [0.0, 1.0], hoặc None nếu thiếu/không parse được.
    """
    if value is None:
        return None
    try:
        score = float(value)
    except (TypeError, ValueError):
        return None
    if score < 0.0:
        return 0.0
    if score > 1.0:
        return 1.0
    return score


def _policy_candidates_from_tool_calls(tool_calls: list[dict[str, Any]]) -> list[PolicyCandidate]:
    """Chuyển tool_calls thô của Router LLM thành PolicyCandidate.

    Args:
        tool_calls: Danh sách tool call do Router LLM trả về.

    Returns:
        Danh sách PolicyCandidate đã loại trùng tên tool, giữ thứ tự đầu tiên và
        mang theo confidence_score hợp lệ nếu có.
    """
    candidates: list[PolicyCandidate] = []
    for call in _unique_tool_calls(tool_calls):
        name = _tool_call_name(call)
        if not name:
            continue
        args = call.get("args", {})
        confidence = None
        if isinstance(args, dict):
            confidence = _coerce_confidence_score(args.get("confidence_score"))
        candidates.append(PolicyCandidate(name=name, confidence_score=confidence))
    return candidates


def _strip_router_only_args(args: dict[str, Any]) -> dict[str, Any]:
    """Loại metadata chỉ dùng cho router trước khi gọi function thật.

    Args:
        args: Dict tham số lấy từ tool call của Router LLM.

    Returns:
        Dict mới không chứa các khóa router-only như confidence_score.
    """
    return {key: value for key, value in args.items() if key not in ROUTER_ONLY_ARGS}


def _unique_tool_calls(tool_calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
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
    """Tool schemas for Router LLM.

    When ``tools`` is provided (e.g. from presentation/main.py), only those
    registered retrievers are exposed — commenting one out in ``main.py`` takes
    effect immediately. Otherwise fall back to the full catalog registry.

    Args:
        tools: Registry runtime dạng {tool_name: {description, function}} hoặc None.

    Returns:
        Danh sách schema đã copy và gắn optional confidence_score cho retriever.
    """
    if tools:
        return [
            _with_router_confidence_schema(entry["description"])
            for entry in tools.values()
            if isinstance(entry, dict) and "description" in entry
        ]

    from application.router_tool_registry import router_tools_for_llm

    return [
        _with_router_confidence_schema(description)
        for description in router_tools_for_llm()
    ]


async def _execute_tool_call(
    tools: dict[str, Any],
    tool_call: dict[str, Any],
    updated_question: str,
) -> Any:
    """Thực thi một tool call đã qua RetrieverPolicy.

    Args:
        tools: Registry runtime chứa function và schema của từng tool.
        tool_call: Tool call đã được policy giữ lại, có thể còn router-only args.
        updated_question: Câu hỏi cuối cùng sẽ truyền vào tham số query nếu tool hỗ trợ.

    Returns:
        Kết quả thô của function retriever/direct tool sau khi đã strip metadata router.
    """
    import chainlit as cl

    tool_name = _tool_call_name(tool_call)
    if tool_name not in tools:
        raise RuntimeError(
            f"Tool '{tool_name}' is not registered. Register the retriever in tools."
        )

    async with cl.Step(name=f"Retriever: {tool_name}") as step:
        function_to_call = tools[tool_name]["function"]
        function_args = _strip_router_only_args(dict(tool_call.get("args", {})))
        if updated_question and _tool_accepts_query(tools, tool_name):
            function_args["query"] = updated_question

        step.input = f"Tool Input: {function_args}"
        res = await function_to_call(**function_args)
        if isinstance(res, dict):
            res["retriever_name"] = tool_name
        if isinstance(res, dict) and "contexts" in res:
            debug = (res.get("debug") or "").strip()
            if debug:
                step.output = debug
            else:
                step.output = (
                    "\n\n".join(res["contexts"])
                    if res["contexts"]
                    else "Khong tim thay context phu hop."
                )
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


async def handle_tool_calls(
    tools: dict[str, Any],
    tool_calls: list[dict[str, Any]],
    updated_question: str,
) -> list[Any]:
    if not tool_calls:
        return []

    unique_tool_calls = _unique_tool_calls(tool_calls)
    _validate_registered_tools(tools, unique_tool_calls)
    print("policy_tool_calls:", unique_tool_calls)

    return list(
        await asyncio.gather(
            *(
                _execute_tool_call(tools, tool_call, updated_question)
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
    """Lấy tool_calls thô từ Router LLM mà không chạy policy hay retriever.

    Args:
        question: Câu hỏi cần định tuyến.
        tools_for_llm: Danh sách tool schema tùy chọn; nếu có sẽ được gắn thêm
            confidence_score cho retriever trước khi bind.

    Returns:
        Danh sách tool_calls thô do Router LLM trả về.
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
    """Gọi Router LLM để chọn tool theo danh sách schema đã cung cấp.

    Args:
        messages: System/user messages truyền vào Router LLM.
        temperature: Tham số tương thích cũ, hiện không dùng.
        tools: Danh sách tool schema được expose cho Router LLM.
        config: Tham số tương thích cũ, hiện không dùng.
        model: Tham số tương thích cũ, hiện không dùng.

    Returns:
        Danh sách tool_calls do LLM trả về; nếu không có tool call thì trả list rỗng.
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
) -> tuple[list[Any], PolicyDecision]:
    """Định tuyến câu hỏi, áp dụng RetrieverPolicy và trả kèm audit.

    Args:
        question: Câu hỏi người dùng sau bước cập nhật/nguyên văn.
        tools: Registry runtime chứa schema và function của các retriever/direct tool.
        answers: Lịch sử hội thoại dạng messages để Router LLM có thêm ngữ cảnh.

    Returns:
        Tuple gồm danh sách kết quả tool đã chạy và PolicyDecision để log/debug.
    """
    llm_tool_calls = await tool_choice(
        [
            {
                "role": "system",
                "content": tool_picker_prompt,
            },
            *answers,
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

    policy_candidates = _policy_candidates_from_tool_calls(llm_tool_calls)
    policy_decision = evaluate_retriever_policy(question, policy_candidates)
    policy_tool_calls = _build_policy_tool_calls(
        llm_tool_calls,
        policy_decision.final_tools,
    )
    tool_response = await handle_tool_calls(tools, policy_tool_calls, question)
    return tool_response, policy_decision


async def route_question(
    question: str,
    tools: dict[str, Any],
    answers: list[dict[str, str]],
) -> list[Any]:
    tool_response, _ = await route_question_with_audit(question, tools, answers)
    return tool_response
