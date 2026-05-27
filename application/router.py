import asyncio

from adapter.config import build_router_llm, ROUTER_LLM

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

Ví dụ tư duy:

Ví dụ 1 (NHIỀU Ý HỎI):
- Câu hỏi: "Tôi là nam năm nay 18 tuổi thì có được kết hôn không? Và tôi có quyền được yêu cầu hủy kết hôn trái pháp luật của bố mẹ tôi không?"
- Ý 1: Hỏi về độ tuổi kết hôn (Nam 18 tuổi) -> Dùng công cụ `dieu_kien_ket_hon`
- Ý 2: Hỏi về quyền yêu cầu hủy kết hôn trái pháp luật -> Dùng công cụ `ket_hon_trai_phap_luat`
=> BẠN PHẢI GỌI CẢ 2 CÔNG CỤ NÀY.

Ví dụ 2 (MỘT Ý HỎI nhưng CẦN NHIỀU BỐI CẢNH PHÁP LÝ):
- Câu hỏi: "Không đăng ký kết hôn người cha có nghĩa vụ cấp dưỡng cho con không?"
- Bối cảnh pháp lý: "Không đăng ký kết hôn" -> liên quan đến quy định về chung sống như vợ chồng -> Dùng công cụ `chung_song_nhu_vo_chong`
- Nội dung chính: "nghĩa vụ cấp dưỡng cho con" -> Dùng công cụ `nghia_vu_cap_duong`
=> BẠN PHẢI GỌI CẢ 2 CÔNG CỤ NÀY để có đầy đủ căn cứ pháp lý cho câu trả lời.
"""

def _tool_accepts_query(tools: dict[str, any], tool_name: str) -> bool:
    properties = (
        tools[tool_name]["description"]
        .get("function", {})
        .get("parameters", {})
        .get("properties", {})
    )
    return "query" in properties


async def _execute_tool_call(tools: dict[str, any], tool_call: dict[str, any], updated_question):
    import chainlit as cl

    tool_name = tool_call["name"]
    async with cl.Step(name=f"Retriever: {tool_name}") as step:
        function_to_call = tools[tool_name]["function"]
        function_args = dict(tool_call.get("args", {}))
        if updated_question and _tool_accepts_query(tools, tool_name):
            function_args["query"] = updated_question

        step.input = f'Tool Input: {function_args}'
        res = await function_to_call(**function_args)
        if isinstance(res, dict) and "contexts" in res:
            debug = (res.get("debug") or "").strip()
            if debug:
                step.output = debug
            else:
                step.output = (
                    "\n\n".join(res["contexts"])
                    if res["contexts"]
                    else "Không tìm thấy context phù hợp."
                )
        elif isinstance(res, list):
            parts = [str(item) for item in res if item is not None]
            step.output = (
                "\n\n".join(parts)
                if parts
                else "Không tìm thấy context phù hợp."
            )
        else:
            step.output = str(res)
        step.metadata = {"raw_result": res}
        return res


async def handle_tool_calls(tools: dict[str, any], llm_tool_calls: list[dict[str, any]], updated_question):
    if not llm_tool_calls:
        return []

    print("llm_tool_calls:", llm_tool_calls)

    seen_tools = set()
    unique_tool_calls = []
    for tool_call in llm_tool_calls:
        tool_name = tool_call["name"]
        if tool_name in seen_tools:
            continue
        seen_tools.add(tool_name)
        unique_tool_calls.append(tool_call)

    return list(
        await asyncio.gather(
            *(
                _execute_tool_call(tools, tool_call, updated_question)
                for tool_call in unique_tool_calls
            )
        )
    )

async def tool_choice(messages, temperature=0, tools=[], config={}, model=None):
    # Cấu hình Gemini (tạm comment):
    # res = await ainvoke_router_with_tools(messages, tools)
    llm = build_router_llm()
    llm_with_tools = llm.bind_tools(tools, tool_choice="any")
    res = await llm_with_tools.ainvoke(messages)
    if not res.tool_calls:
        print(f"[Router] No tool_calls returned. model={ROUTER_LLM} content={res.content}")
    return res.tool_calls

async def route_question(question: str, tools: dict[str, any], answers: list[dict[str, str]]):
    llm_tool_calls = await tool_choice(
        [
            {
                "role": "system",
                "content": tool_picker_prompt,
            },
            *answers,
            {
                "role": "user",
                "content": f"Câu hỏi của người dùng cần tìm công cụ để giải quyết: '{question}'",
            },
        ],
        tools=[tool["description"] for tool in tools.values()],
    )
    return await handle_tool_calls(tools, llm_tool_calls, question)
