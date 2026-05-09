from adapter.config import build_llm, ROUTER_LLM

tool_picker_prompt = """
Bạn là một hệ thống định tuyến (Router Agent) thông minh.
Nhiệm vụ của bạn là đọc câu hỏi của người dùng và chọn ĐÚNG và ĐỦ các công cụ (tools) để giải quyết TOÀN BỘ câu hỏi.

QUY TẮC BẮT BUỘC (CRITICAL RULES):
1. PHÂN TÍCH NHIỀU Ý: Người dùng thường hỏi nhiều vấn đề trong cùng 1 câu. Bạn PHẢI bóc tách từng vế của câu hỏi.
2. Tùy vào câu hỏi có thể cần phải gọi nhiều tool khác nhau. Nhưng không gọi cùng 1 tool nhiều lần.
3. ĐIỀN ĐỦ THAM SỐ: Đảm bảo tham số `query` chứa nguyên văn ý hỏi của người dùng cho công cụ đó.

Ví dụ tư duy:
- Câu hỏi: "Tôi là nam năm nay 18 tuổi thì có được kết hôn không? Và tôi có quyền được yêu cầu hủy kết hôn trái pháp luật của bố mẹ tôi không?"
- Ý 1: Hỏi về độ tuổi kết hôn (Nam 18 tuổi) -> Dùng công cụ `dieu_kien_ket_hon`
- Ý 2: Hỏi về quyền yêu cầu hủy kết hôn trái pháp luật -> Dùng công cụ `ket_hon_trai_phap_luat`
=> BẠN PHẢI GỌI CẢ 2 CÔNG CỤ NÀY.
"""

async def handle_tool_calls(tools: dict[str, any], llm_tool_calls: list[dict[str, any]], updated_question):
    output = []
    called_tools = set()
    if llm_tool_calls:
        import chainlit as cl
        print('llm_tool_calls:', llm_tool_calls)
        for tool_call in llm_tool_calls:
            tool_name = tool_call['name']

            if tool_name in called_tools:
                continue

            called_tools.add(tool_name)

            async with cl.Step(name=f"Tool: {tool_name}") as step:
                function_to_call = tools[tool_name]["function"]
                function_args = {
                    "query": updated_question
                } if updated_question else tool_call.get("args", {})
                
                step.input = function_args
                res = await function_to_call(**function_args)
                step.output = res
                
                output.append(res)
    return output

async def tool_choice(messages, temperature=0, tools=[], config={}, model=None):
    llm = build_llm(model=ROUTER_LLM, temperature=0, max_tokens=2048)
    llm_with_tools = llm.bind_tools(tools)
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
