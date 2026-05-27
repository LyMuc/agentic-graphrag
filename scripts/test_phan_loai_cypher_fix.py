"""Smoke test: params chỉ từ embedding (Neo4j vector hoặc memory), không rule."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from adapter.config import driver
from adapter.retrievers.quan_he_giua_vo_va_chong.graph_param_resolver import (
    build_params_for_intent,
)
from adapter.retrievers.quan_he_giua_vo_va_chong.intent_cypher_templates import (
    INTENT_DIEU_KIEN_HANH_VI,
    INTENT_PHAN_LOAI_TAI_SAN,
    INTENT_TINH_HUONG_TONG_HOP,
    run_graph_retrieval,
)
from adapter.retrievers.quan_he_giua_vo_va_chong.semantic_embedding import (
    EMBEDDING_FALLBACK_TOP_K,
    EMBEDDING_MIN_SCORE,
    neo4j_vector_index_exists,
)

QUERY = "vợ mua nhà cho nhân tình chồng có đòi được không?"
MAX_PHAN_LOAI_TRIPLES = 40


def _count_triples(block: dict) -> int:
    return len(block.get("graph_triples") or [])


def main() -> int:
    print(f"Neo4j vector index exists: {neo4j_vector_index_exists()}")
    print(f"EMBEDDING_MIN_SCORE: {EMBEDDING_MIN_SCORE}")
    print(f"EMBEDDING_FALLBACK_TOP_K: {EMBEDDING_FALLBACK_TOP_K}")
    print(f"Query: {QUERY}\n")

    composite_params, composite_meta = build_params_for_intent(QUERY, INTENT_TINH_HUONG_TONG_HOP)
    pl_params, pl_meta = build_params_for_intent(QUERY, INTENT_PHAN_LOAI_TAI_SAN)
    dk_params, dk_meta = build_params_for_intent(QUERY, INTENT_DIEU_KIEN_HANH_VI)

    print("=== phan_loai params ===")
    print(pl_params)
    if pl_meta:
        print("top match:", pl_meta[0])
    print()

    print("=== dieu_kien params ===")
    print(dk_params)
    if dk_meta:
        print("top match:", dk_meta[0])
    print()

    pl_graph = run_graph_retrieval(driver, INTENT_PHAN_LOAI_TAI_SAN, pl_params)
    dk_graph = run_graph_retrieval(driver, INTENT_DIEU_KIEN_HANH_VI, dk_params)

    print(f"phan_loai graph_triples: {_count_triples(pl_graph)}")
    print(f"dieu_kien graph_triples: {_count_triples(dk_graph)}")
    print(f"dieu_kien can_cu: {dk_graph.get('can_cu_ids')}")
    print()

    failures: list[str] = []
    if not pl_meta and not dk_meta:
        failures.append("Không có embedding match — cần GOOGLE_API_KEY/GEMINI_API_KEY + setup vector index")

    def _check_matches(match_items: list[dict], used_fallback: bool) -> None:
        by_label: dict[str, list[dict]] = {}
        for m in match_items:
            if m.get("method") == "text":
                failures.append("Vẫn còn text/rule match (method=text)")
            if not m.get("used_fallback") and m.get("score", 0) < EMBEDDING_MIN_SCORE:
                failures.append(f"Match dưới ngưỡng (không fallback): {m}")
            by_label.setdefault(m.get("label", ""), []).append(m)
        if used_fallback:
            for label, items in by_label.items():
                if len(items) > EMBEDDING_FALLBACK_TOP_K:
                    failures.append(
                        f"Fallback label {label} vượt top-{EMBEDDING_FALLBACK_TOP_K}: {len(items)} matches"
                    )

    for block in composite_meta:
        _check_matches(block.get("matches") or [], bool(block.get("used_fallback")))
    _check_matches(pl_meta, any(m.get("used_fallback") for m in pl_meta))
    _check_matches(dk_meta, any(m.get("used_fallback") for m in dk_meta))
    if _count_triples(pl_graph) > MAX_PHAN_LOAI_TRIPLES:
        failures.append(f"phan_loai vẫn quá nhiều triple: {_count_triples(pl_graph)}")

    if failures:
        print("FAILED:")
        for f in failures:
            print(f"  - {f}")
        return 1

    print("PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
