"""Back-compat shim — moved vào gói cypher_templates (Phase 3).

Vị trí mới: ``server.infrastructure.neo4j.cypher_templates._context_tho_common``.
Copy toàn bộ namespace (gồm cả tên tiền tố ``_``) để script cũ vẫn dùng được.
"""
from server.infrastructure.neo4j.cypher_templates import _context_tho_common as _src

globals().update(
    {name: value for name, value in vars(_src).items() if not name.startswith("__")}
)
del _src


import warnings as _warnings

_warnings.warn(
    f"{__name__} là shim back-compat (refactor sang cây server/); "
    "hãy import từ vị trí server.* mới. Shim sẽ bị gỡ ở PR sau.",
    DeprecationWarning,
    stacklevel=2,
)
