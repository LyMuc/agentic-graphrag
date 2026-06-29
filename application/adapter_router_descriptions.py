"""Back-compat shim — moved to ``server.agents.retrievers._descriptions`` (Phase 3)."""
from server.agents.retrievers._descriptions import *  # noqa: F401,F403
from server.agents.retrievers._descriptions import (  # noqa: F401
    ADAPTER_DESCRIPTION_SOURCES,
    enrich_specs_with_adapter_descriptions,
)


import warnings as _warnings

_warnings.warn(
    f"{__name__} là shim back-compat (refactor sang cây server/); "
    "hãy import từ vị trí server.* mới. Shim sẽ bị gỡ ở PR sau.",
    DeprecationWarning,
    stacklevel=2,
)
