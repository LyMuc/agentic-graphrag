"""Back-compat shim — moved to ``server.app.routes.projects`` (Phase 5).

Import side-effect (``@cl.on_app_startup`` + ``app.include_router``) chạy đúng một
lần khi module mới được nạp lần đầu — không double-include.
"""
from server.app.routes.projects import *  # noqa: F401,F403


import warnings as _warnings

_warnings.warn(
    f"{__name__} là shim back-compat (refactor sang cây server/); "
    "hãy import từ vị trí server.* mới. Shim sẽ bị gỡ ở PR sau.",
    DeprecationWarning,
    stacklevel=2,
)
