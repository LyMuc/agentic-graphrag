#!/usr/bin/env python3
"""
Gắn embedding lên node semantic :CheDoTaiSanCuaVoChong và tạo vector index Neo4j.

Chạy từ root repo (cần .env với NEO4J_* và GOOGLE_API_KEY / GEMINI_API_KEY):

    python scripts/setup_neo4j_semantic_embeddings.py
    python scripts/setup_neo4j_semantic_embeddings.py --dry-run
    python scripts/setup_neo4j_semantic_embeddings.py --query "vợ mua nhà cho nhân tình chồng có đòi được không?"

Sau khi setup, retriever dùng vector index Neo4j:
    NEO4J_VECTOR_INDEX=che_do_tai_san_semantic_embedding
    CALL db.index.vector.queryNodes(...)

Lưu ý: Đang dùng Gemini embedding (gemini-embedding-001, 768 dims).
Để quay lại OpenAI: uncomment khối OpenAI trong semantic_embedding.py + cập nhật .env.

# OpenAI (tạm comment):
# Cần OPENAI_API_KEY trực tiếp (Vercel AI Gateway thường KHÔNG hỗ trợ /embeddings).
# Hoặc EMBEDDING_API_KEY + EMBEDDING_BASE_URL.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from adapter.retrievers.quan_he_giua_vo_va_chong.graph_param_resolver import (  # noqa: E402
    build_params_for_intent,
)
from adapter.retrievers.quan_he_giua_vo_va_chong.intent_cypher_templates import (  # noqa: E402
    INTENT_DIEU_KIEN_HANH_VI,
    INTENT_PHAN_LOAI_TAI_SAN,
    INTENT_TINH_HUONG_TONG_HOP,
)
from adapter.retrievers.quan_he_giua_vo_va_chong.semantic_embedding import (  # noqa: E402
    EMBEDDING_DIMENSIONS,
    EMBEDDING_MIN_SCORE,
    EMBEDDING_MODEL,
    NEO4J_VECTOR_INDEX,
    create_vector_index,
    embed_texts,
    load_semantic_nodes,
    neo4j_vector_index_exists,
    query_semantic_nodes_by_vector,
    write_node_embeddings,
)
from adapter.retrievers.quan_he_giua_vo_va_chong.semantic_embedding import embed_query  # noqa: E402


def setup_embeddings(force: bool = False) -> None:
    nodes = load_semantic_nodes()
    if not nodes:
        print("Không tìm thấy node semantic trong Neo4j.")
        return

    print(f"Model: {EMBEDDING_MODEL} ({EMBEDDING_DIMENSIONS} dims)")
    print(f"Nodes: {len(nodes)}")

    ids = [n["id"] for n in nodes]
    vectors = embed_texts(ids)
    if not vectors:
        raise RuntimeError("Embedding trả về rỗng.")
    if len(vectors[0]) != EMBEDDING_DIMENSIONS:
        raise RuntimeError(
            f"Vector dim={len(vectors[0])} ≠ EMBEDDING_DIMENSIONS={EMBEDDING_DIMENSIONS}. "
            "Cập nhật EMBEDDING_DIMENSIONS trong .env."
        )

    updated = write_node_embeddings(ids, vectors)
    print(f"Đã ghi embedding lên {updated} node.")

    create_vector_index()
    print(f"Vector index: {NEO4J_VECTOR_INDEX} (exists={neo4j_vector_index_exists()})")


def smoke_query(text: str) -> None:
    if not neo4j_vector_index_exists():
        print("Vector index chưa tồn tại. Chạy setup trước (bỏ --dry-run).")
        return
    qvec = embed_query(text)
    rows = query_semantic_nodes_by_vector(
        qvec,
        allowed_labels=["TaiSan", "HanhViPhapLy", "KhaiNiemPhapLy"],
        min_score=EMBEDDING_MIN_SCORE,
    )
    print(f"\nMatches (score >= {EMBEDDING_MIN_SCORE}) cho: {text!r}")
    for row in rows:
        print(f"  [{row['score']:.4f}] {row['label']}: {row['id']}")
    if not rows:
        print("  (không có node nào đạt ngưỡng)")


def smoke_params(text: str) -> None:
    composite, meta = build_params_for_intent(text, INTENT_TINH_HUONG_TONG_HOP)
    print(f"\nComposite params cho: {text!r}")
    for block in meta:
        print(f"  sub_intent={block['sub_intent']}")
        print(f"    params={block['params']}")
        for m in (block.get("matches") or [])[:3]:
            print(f"    match [{m['method']} {m['score']}] {m['label']}: {m['node_id']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Setup Neo4j vector embeddings cho semantic graph.")
    parser.add_argument("--dry-run", action="store_true", help="Chỉ liệt kê node, không ghi DB.")
    parser.add_argument("--force", action="store_true", help="Ghi lại embedding (hiện luôn ghi đè).")
    parser.add_argument("--query", type=str, help="Smoke test vector search sau setup.")
    args = parser.parse_args()

    if args.dry_run:
        nodes = load_semantic_nodes()
        print(f"[dry-run] {len(nodes)} semantic nodes sẽ được embed.")
        by_label: dict[str, int] = {}
        for n in nodes:
            by_label[n["label"]] = by_label.get(n["label"], 0) + 1
        for label, count in sorted(by_label.items()):
            print(f"  {label}: {count}")
        return 0

    setup_embeddings(force=args.force)

    if args.query:
        smoke_query(args.query)
        smoke_params(args.query)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
