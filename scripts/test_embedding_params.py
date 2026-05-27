"""Smoke test: LLM-free param resolution via stored embeddings."""
from __future__ import annotations

from adapter.config import driver
from adapter.retrievers.quan_he_giua_vo_va_chong.graph_param_resolver import resolve_graph_params
from adapter.retrievers.quan_he_giua_vo_va_chong.intent_cypher_templates import (
    INTENT_DIEU_KIEN_HANH_VI,
    run_graph_retrieval,
)

QUERY = (
    "Chiếm hữu, sử dụng, định đoạt tài sản riêng được quy định như thế nào theo pháp luật?"
)


def main() -> None:
    params, meta, fallback = resolve_graph_params(QUERY, INTENT_DIEU_KIEN_HANH_VI)
    print("query:", QUERY)
    print("fallback:", fallback)
    print("params:", params)
    for m in meta:
        print(f"  [{m['score']}] {m['label']}: {m['node_id'][:80]}")

    graph = run_graph_retrieval(driver, INTENT_DIEU_KIEN_HANH_VI, params)
    print("graph hanh_vi:", graph.get("hanh_vi"))
    print("triples:", len(graph.get("graph_triples") or []))
    print("can_cu:", graph.get("can_cu_ids"))


if __name__ == "__main__":
    main()
