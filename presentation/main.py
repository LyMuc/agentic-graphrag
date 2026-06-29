import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import chainlit as cl
# Gọi data_layer để Chainlit thiết lập PostgreSQL connection lúc khởi động
from adapter import data_layer  # noqa: F401
from chainlit.server import app
import presentation.projects_api  # noqa: F401
from presentation.viz_routes import register_viz_routes
from presentation.guest_auth import guest_management_guard, router as guest_router
from chainlit.types import ThreadDict
from typing import Dict, Optional

from server.agents.router.agent import RouterAgent
from server.agents.synthesizer.agent import SynthesizerAgent
from server.conversation.orchestrator import ConversationOrchestrator

app.middleware("http")(guest_management_guard)
app.include_router(guest_router)
register_viz_routes(app)

# Lớp điều phối phiên (deterministic, KHÔNG có LLM) — bọc RouterAgent + SynthesizerAgent.
orchestrator = ConversationOrchestrator(
    router=RouterAgent(),
    synthesizer=SynthesizerAgent(),
)


# =================================================================
# AUTHENTICATION HOOKS (OAUTH)
# =================================================================
@cl.oauth_callback
def oauth_callback(
    provider_id: str,
    token: str,
    raw_user_data: Dict[str, str],
    default_user: cl.User,
) -> Optional[cl.User]:
    """
    Xử lý thông tin trả về sau khi người dùng đăng nhập Google/Github thành công.
    Map vào identifier để PostgreSQL lưu trữ user mới.
    """
    identifier = raw_user_data.get("email") or raw_user_data.get("login") or str(raw_user_data.get("id"))
    name = raw_user_data.get("name") or identifier

    metadata = {
        "name": name,
        "avatar_url": raw_user_data.get("avatar_url") or raw_user_data.get("picture"),
        "provider": provider_id
    }

    return cl.User(
        identifier=identifier,
        metadata=metadata
    )


# =================================================================
# CHAT LIFECYCLE HOOKS — delegate vào ConversationOrchestrator
# =================================================================
@cl.on_chat_start
async def on_chat_start():
    await orchestrator.on_chat_start()


@cl.on_chat_resume
async def on_chat_resume(thread: ThreadDict):
    await orchestrator.on_chat_resume(thread)


@cl.on_message
async def main(message: cl.Message):
    await orchestrator.on_message(message)
