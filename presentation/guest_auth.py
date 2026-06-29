"""Back-compat shim — moved to ``server.app.routes.guest_auth`` (Phase 5)."""
from server.app.routes.guest_auth import *  # noqa: F401,F403
from server.app.routes.guest_auth import (  # noqa: F401
    guest_auth,
    guest_management_guard,
    is_guest_management_request,
    router,
)
