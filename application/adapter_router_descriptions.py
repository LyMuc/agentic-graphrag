"""Back-compat shim — moved to ``server.agents.retrievers._descriptions`` (Phase 3)."""
from server.agents.retrievers._descriptions import *  # noqa: F401,F403
from server.agents.retrievers._descriptions import (  # noqa: F401
    ADAPTER_DESCRIPTION_SOURCES,
    enrich_specs_with_adapter_descriptions,
)
