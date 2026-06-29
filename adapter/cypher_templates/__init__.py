"""Back-compat shim — moved to ``server.infrastructure.neo4j.cypher_templates`` (Phase 3).

Tái xuất các tên cấp cao (``CypherTemplate``, ``TemplateRegistry``, ...) và trỏ
``__path__`` sang gói mới để mọi import sâu cũ
(``adapter.cypher_templates.<topic>.<module>``) vẫn phân giải được.
"""
from server.infrastructure.neo4j.cypher_templates import *  # noqa: F401,F403
from server.infrastructure.neo4j.cypher_templates import __path__ as _new_path

__path__ = list(_new_path)


import warnings as _warnings

_warnings.warn(
    f"{__name__} là shim back-compat (refactor sang cây server/); "
    "hãy import từ vị trí server.* mới. Shim sẽ bị gỡ ở PR sau.",
    DeprecationWarning,
    stacklevel=2,
)
