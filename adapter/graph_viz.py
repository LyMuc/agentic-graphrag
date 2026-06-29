"""Back-compat shim — moved to ``server.infrastructure.viz.graph_viz`` (Phase 2).

Một số script import cả các symbol tiền tố ``_`` (vd. ``_GraphBuilder``,
``_collect_ids_from_context``) nên shim copy toàn bộ namespace, không chỉ ``import *``.
"""
from server.infrastructure.viz import graph_viz as _graph_viz

globals().update(
    {name: value for name, value in vars(_graph_viz).items() if not name.startswith("__")}
)
del _graph_viz
