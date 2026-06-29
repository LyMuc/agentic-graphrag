"""Back-compat shim — moved to ``server.app.routes.guest_auth`` (Phase 5)."""
from server.app.routes.guest_auth import *  # noqa: F401,F403
from server.app.routes.guest_auth import (  # noqa: F401
    guest_auth,
    guest_management_guard,
    is_guest_management_request,
    router,
)


import warnings as _warnings

_warnings.warn(
    f"{__name__} là shim back-compat (refactor sang cây server/); "
    "hãy import từ vị trí server.* mới. Shim sẽ bị gỡ ở PR sau.",
    DeprecationWarning,
    stacklevel=2,
)
