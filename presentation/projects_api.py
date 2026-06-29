"""Back-compat shim — moved to ``server.app.routes.projects`` (Phase 5).

Import side-effect (``@cl.on_app_startup`` + ``app.include_router``) chạy đúng một
lần khi module mới được nạp lần đầu — không double-include.
"""
from server.app.routes.projects import *  # noqa: F401,F403
