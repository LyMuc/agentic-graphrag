"""Back-compat shim — tách thành gói ``server.agents.router`` (Phase 4).

Re-export đầy đủ API (gồm cả các helper tiền tố ``_`` mà test/benchmark dùng).
"""
from server.agents.router import *  # noqa: F401,F403
from server.agents.router import (  # noqa: F401
    RETRIEVER_QUERY_PARAM_DESCRIPTION,
    ROUTER_ONLY_ARGS,
    RouterAgent,
    _CONTROL_ARGS,
    _execute_or_reuse_tool_call,
    _execute_tool_call,
    _render_retriever_contexts_for_ui,
    _resolved_query,
    _reuse_tool_call,
    _router_tool_descriptions,
    _strip_router_only_args,
    _tool_accepts_query,
    _tool_call_name,
    _tool_function_args,
    _tool_schema_name,
    _unique_tool_calls,
    _validate_registered_tools,
    _with_router_confidence_schema,
    handle_tool_calls,
    llm_candidate_names,
    llm_retriever_candidates,
    route_question,
    route_question_with_audit,
    tool_choice,
    tool_picker_prompt,
)


import warnings as _warnings

_warnings.warn(
    f"{__name__} là shim back-compat (refactor sang cây server/); "
    "hãy import từ vị trí server.* mới. Shim sẽ bị gỡ ở PR sau.",
    DeprecationWarning,
    stacklevel=2,
)
