"""RouterAgent — tác tử định tuyến không trạng thái.

Mỗi lần được gọi, RouterAgent đọc câu hỏi hiện tại cùng tóm tắt bộ nhớ
retrieval, dùng LLM tool calling để chọn zero hoặc nhiều retriever phù
hợp. Các retriever được gọi song song bằng `asyncio.gather`, kết quả
được trả về dưới dạng danh sách `RetrieverResult` đã chuẩn hoá. Khi
Router quyết định tái sử dụng ngữ cảnh đã lưu (`context_action="reuse"`),
RouterAgent sẽ chạy qua bước kiểm tra deterministic trước khi trả ngữ
cảnh cũ thay vì gọi retriever thật.

Tách từ ``application/router.py`` thành prompt / schema / reuse / agent.
"""
from server.agents.router.prompt import (
    RETRIEVER_QUERY_PARAM_DESCRIPTION,
    tool_picker_prompt,
)
from server.agents.router.schema import (
    ROUTER_ONLY_ARGS,
    _CONTROL_ARGS,
    _resolved_query,
    _router_tool_descriptions,
    _strip_router_only_args,
    _tool_accepts_query,
    _tool_call_name,
    _tool_function_args,
    _tool_schema_name,
    _unique_tool_calls,
    _validate_registered_tools,
    _with_router_confidence_schema,
)
from server.agents.router.reuse import (
    _execute_or_reuse_tool_call,
    _execute_tool_call,
    _render_retriever_contexts_for_ui,
    _reuse_tool_call,
    handle_tool_calls,
)
from server.agents.router.agent import (
    RouterAgent,
    llm_candidate_names,
    llm_retriever_candidates,
    route_question,
    route_question_with_audit,
    tool_choice,
)

__all__ = [
    "RETRIEVER_QUERY_PARAM_DESCRIPTION",
    "tool_picker_prompt",
    "ROUTER_ONLY_ARGS",
    "RouterAgent",
    "handle_tool_calls",
    "llm_candidate_names",
    "llm_retriever_candidates",
    "route_question",
    "route_question_with_audit",
    "tool_choice",
]
