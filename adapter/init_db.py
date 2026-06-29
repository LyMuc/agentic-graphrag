"""Back-compat shim — moved to ``server.infrastructure.persistence.init_db`` (Phase 2)."""
from server.infrastructure.persistence.init_db import *  # noqa: F401,F403
from server.infrastructure.persistence.init_db import migrate_db

if __name__ == "__main__":
    import asyncio

    asyncio.run(migrate_db())
    print("Database migrations completed successfully.")


import warnings as _warnings

_warnings.warn(
    f"{__name__} là shim back-compat (refactor sang cây server/); "
    "hãy import từ vị trí server.* mới. Shim sẽ bị gỡ ở PR sau.",
    DeprecationWarning,
    stacklevel=2,
)
