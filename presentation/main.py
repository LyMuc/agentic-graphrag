"""Back-compat shim — moved to ``server.app.main`` (Phase 5).

Nạp module mới sẽ đăng ký mọi Chainlit hook + mount routes (qua decorator/side
effect), nên ``chainlit run presentation/main.py`` vẫn chạy được. Giữ thêm
``main_prompt`` + ``tools`` cho các benchmark script cũ.
"""
from server.app.main import *  # noqa: F401,F403
from server.app.main import orchestrator  # noqa: F401
from server.agents.synthesizer.agent import main_prompt  # noqa: F401

# Back-compat: benchmark cũ dùng ``from presentation.main import main_prompt, tools``.
tools = orchestrator.tools
