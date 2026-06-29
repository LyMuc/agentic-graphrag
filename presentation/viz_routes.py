"""Back-compat shim — moved to ``server.app.routes.viz`` (Phase 5)."""
from server.app.routes.viz import *  # noqa: F401,F403
from server.app.routes.viz import register_viz_routes  # noqa: F401
