#!/usr/bin/env python3
"""
Quét cosine similarity giữa câu hỏi và TOÀN BỘ node :CheDoTaiSanCuaVoChong.

Dùng embedding đã lưu trên node (property `embedding`); node chưa có embedding
sẽ được embed id tại chỗ.

Ví dụ:
    python scripts/scan_semantic_embedding_similarity.py
    python scripts/scan_semantic_embedding_similarity.py --query "Chồng mua nhà cho nhân tình, vợ có đòi được hay không?"
    python scripts/scan_semantic_embedding_similarity.py --min-score 0.85
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from adapter.retrievers.quan_he_giua_vo_va_chong.intent_cypher_templates import DOMAIN_LABEL  # noqa: E402
from adapter.retrievers.quan_he_giua_vo_va_chong.semantic_embedding import (  # noqa: E402
    EMBEDDING_MIN_SCORE,
    EMBEDDING_MODEL,
    EMBEDDING_PROPERTY,
    embed_query,
    embed_texts,
)
from adapter.config import driver  # noqa: E402


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def load_all_domain_nodes() -> list[dict]:
    records, _, _ = driver.execute_query(
        f"""
        MATCH (n:{DOMAIN_LABEL})
        WHERE n.id IS NOT NULL
        RETURN n.id AS id,
               head([lbl IN labels(n) WHERE lbl <> '{DOMAIN_LABEL}']) AS label,
               n.{EMBEDDING_PROPERTY} AS embedding
        ORDER BY label, id
        """
    )
    return [
        {
            "id": r["id"],
            "label": r.get("label") or "(unknown)",
            "embedding": r.get("embedding"),
        }
        for r in records
        if r.get("id")
    ]


def scan_similarity(query: str, min_score: float) -> tuple[list[dict], dict[str, int]]:
    nodes = load_all_domain_nodes()
    if not nodes:
        print("Không tìm thấy node :CheDoTaiSanCuaVoChong trong Neo4j.")
        return [], {}

    query_vec = embed_query(query)

    missing = [n for n in nodes if not n.get("embedding")]
    if missing:
        print(f"Embed tại chỗ {len(missing)} node chưa có property `{EMBEDDING_PROPERTY}`...")
        vecs = embed_texts([n["id"] for n in missing])
        for node, vec in zip(missing, vecs):
            node["embedding"] = vec

    hits: list[dict] = []
    stats = {"total": len(nodes), "with_embedding": len(nodes) - len(missing), "embedded_on_fly": len(missing)}

    for node in nodes:
        vec = node.get("embedding")
        if not vec:
            continue
        score = _cosine_similarity(query_vec, vec)
        if score > min_score:
            hits.append(
                {
                    "id": node["id"],
                    "label": node["label"],
                    "score": score,
                }
            )

    hits.sort(key=lambda x: x["score"], reverse=True)
    return hits, stats


def print_report(query: str, min_score: float, hits: list[dict], stats: dict[str, int]) -> None:
    by_label: dict[str, list[dict]] = defaultdict(list)
    for hit in hits:
        by_label[hit["label"]].append(hit)

    print(f"Model: {EMBEDDING_MODEL}")
    print(f"Câu hỏi: {query!r}")
    print(f"Ngưỡng: cosine_similarity > {min_score}")
    print(f"Tổng node :{DOMAIN_LABEL}: {stats.get('total', 0)}")
    print(f"  - Đã có embedding trên DB: {stats.get('with_embedding', 0)}")
    print(f"  - Embed tại chỗ: {stats.get('embedded_on_fly', 0)}")
    print(f"Node vượt ngưỡng: {len(hits)}")
    print()

    if not hits:
        print("(Không có node nào có similarity > ngưỡng)")
        return

    for label in sorted(by_label.keys()):
        items = by_label[label]
        print(f"=== {label} ({len(items)} node) ===")
        for item in sorted(items, key=lambda x: x["score"], reverse=True):
            print(f"  [{item['score']:.4f}] {item['id']}")
        print()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    parser = argparse.ArgumentParser(
        description="Quét cosine similarity câu hỏi vs toàn bộ node CheDoTaiSanCuaVoChong."
    )
    parser.add_argument(
        "--query",
        type=str,
        default="Chồng mua nhà cho nhân tình, vợ có đòi được hay không?",
        help="Câu hỏi cần embed và so khớp.",
    )
    parser.add_argument(
        "--min-score",
        type=float,
        default=EMBEDDING_MIN_SCORE,
        help=f"Chỉ liệt kê node có score > min_score (mặc định {EMBEDDING_MIN_SCORE}).",
    )
    parser.add_argument(
        "--show-top",
        type=int,
        default=0,
        metavar="N",
        help="Nếu > 0, in thêm top-N node mỗi label (kể cả dưới ngưỡng).",
    )
    args = parser.parse_args()

    hits, stats = scan_similarity(args.query, args.min_score)
    print_report(args.query, args.min_score, hits, stats)

    if args.show_top > 0 and not hits:
        all_hits, _ = scan_similarity(args.query, min_score=-1.0)
        by_label: dict[str, list[dict]] = defaultdict(list)
        for hit in all_hits:
            by_label[hit["label"]].append(hit)
        print(f"--- Top-{args.show_top} mỗi label (dưới ngưỡng {args.min_score}) ---")
        for label in sorted(by_label.keys()):
            items = sorted(by_label[label], key=lambda x: x["score"], reverse=True)[: args.show_top]
            print(f"\n=== {label} ===")
            for item in items:
                print(f"  [{item['score']:.4f}] {item['id']}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
