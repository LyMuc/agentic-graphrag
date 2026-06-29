"""Back-compat shim — tách thành ``server.conversation.memory`` + ``history`` (Phase 4)."""
from server.conversation.memory import *  # noqa: F401,F403
from server.conversation.history import *  # noqa: F401,F403
from server.conversation.memory import (  # noqa: F401
    ReuseValidation,
    build_turn_anchor,
    create_retrieval_memory_entries,
    current_kg_version,
    restore_conversation_state,
    retrieval_memory_summary,
    validate_reuse_request,
)
from server.conversation.history import (  # noqa: F401
    RESPONSE_HISTORY_MAX_TOKENS,
    ROUTER_HISTORY_MAX_TOKENS,
    build_working_history,
    context_refs_from_messages,
    estimate_tokens,
)


import warnings as _warnings

_warnings.warn(
    f"{__name__} là shim back-compat (refactor sang cây server/); "
    "hãy import từ vị trí server.* mới. Shim sẽ bị gỡ ở PR sau.",
    DeprecationWarning,
    stacklevel=2,
)
