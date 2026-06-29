"""Back-compat shim — moved to ``server.app.routes.viz`` (Phase 5)."""
from server.app.routes.viz import *  # noqa: F401,F403
from server.app.routes.viz import register_viz_routes  # noqa: F401


import warnings as _warnings

_warnings.warn(
    f"{__name__} là shim back-compat (refactor sang cây server/); "
    "hãy import từ vị trí server.* mới. Shim sẽ bị gỡ ở PR sau.",
    DeprecationWarning,
    stacklevel=2,
)
