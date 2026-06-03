"""Quick LLM intent smoke test (requires OPENAI_API_KEY)."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from adapter.retrievers.quan_he_giua_vo_va_chong.che_do_tai_san_cua_vo_chong_v2 import (
    che_do_tai_san_cua_vo_chong_v2,
)

QUERY = (
    "Chiếm hữu, sử dụng, định đoạt tài sản riêng được quy định như thế nào theo pháp luật?"
)


async def main() -> None:
    result = await che_do_tai_san_cua_vo_chong_v2(QUERY)
    print("intent_source:", result.get("intent_source"))
    print("llm_templates:", result.get("llm_templates"))
    print("intents:", result.get("intents"))
    print("params:", result.get("params"))
    graph_ctx = result.get("graph_context") or {}
    if isinstance(graph_ctx, list):
        for block in graph_ctx:
            print("can_cu:", (block or {}).get("can_cu_ids"))
    else:
        print("can_cu (graph):", graph_ctx.get("can_cu_ids"))


if __name__ == "__main__":
    asyncio.run(main())
