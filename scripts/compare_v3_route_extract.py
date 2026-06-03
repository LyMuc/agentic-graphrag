"""So sánh route+extract 1-call vs legacy (classify + extract) cho retriever v3.

Usage:
  python scripts/compare_v3_route_extract.py --topic chia_tai_san --limit 5
  python scripts/compare_v3_route_extract.py --topic tai_san --limit 3 --dry-run

Cần OPENAI_API_KEY (hoặc env LLM tương đương) khi không dùng --dry-run.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from adapter.cypher_templates.router_schema import build_route_extract_schema


def _load_questions(topic: str, limit: int) -> list[str]:
    if topic == "chia_tai_san":
        path = ROOT / "benchmark_dataset/feat_llm/chia_tai_san_sau_ly_hon.json"
    else:
        path = ROOT / "benchmark_dataset/feat_llm/che_do_tai_san_cua_vo_chong.json"
    if not path.exists():
        return [
            "Tài sản chung và riêng khác nhau thế nào?",
            "Khi ly hôn nhà trả góp chia ra sao?",
        ][:limit]
    data = json.loads(path.read_text(encoding="utf-8"))
    return [item["question"] for item in data[:limit]]


def _snapshot(routed) -> list[dict]:
    return [
        {
            "template_name": c.template_name,
            "reason": c.reason,
            "thoi_diem_su_kien": c.thoi_diem_su_kien,
            "params": c.params.model_dump(),
        }
        for c in routed
    ]


async def _run_topic(topic: str, limit: int, dry_run: bool) -> int:
    questions = _load_questions(topic, limit)
    if dry_run:
        from adapter.cypher_templates.chia_tai_san_sau_ly_hon import (
            CHIA_TAI_SAN_SAU_LY_HON_REGISTRY,
        )
        from adapter.cypher_templates.tai_san import TAI_SAN_REGISTRY

        reg = (
            CHIA_TAI_SAN_SAU_LY_HON_REGISTRY
            if topic == "chia_tai_san"
            else TAI_SAN_REGISTRY
        )
        mx = 2 if topic == "chia_tai_san" else 3
        combined, _ = build_route_extract_schema(reg, max_choices=mx)
        print(f"[dry-run] {topic}: schema={combined.__name__}, n={len(questions)}")
        return 0

    os.environ["RETRIEVER_V3_SINGLE_LLM"] = "0"
    import importlib

    if topic == "chia_tai_san":
        mod = importlib.import_module(
            "adapter.retrievers.ly_hon.chia_tai_san_sau_ly_hon_v3"
        )
        from adapter.cypher_templates.chia_tai_san_sau_ly_hon import (
            CHIA_TAI_SAN_SAU_LY_HON_REGISTRY,
        )

        registry = CHIA_TAI_SAN_SAU_LY_HON_REGISTRY
        classify = mod._classify_templates
        extract = mod._extract_template_params
        post = mod._normalize_with_term_mapping
        classifier_prompt = mod._build_classifier_prompt()
        extract_base = mod._EXTRACT_SYS_PROMPT_BASE
        max_choices = 2
        fallback = "nguyen_tac_chia_tai_san_ly_hon"
        empty_ok = False
    else:
        mod = importlib.import_module(
            "adapter.retrievers.quan_he_giua_vo_va_chong.che_do_tai_san_cua_vo_chong_v3"
        )
        from adapter.cypher_templates.tai_san import TAI_SAN_REGISTRY

        registry = TAI_SAN_REGISTRY
        classify = mod._classify_templates
        extract = mod._extract_template_params
        post = mod._post_process_extracted
        classifier_prompt = mod._build_classifier_prompt()
        extract_base = mod._EXTRACT_SYS_PROMPT_BASE
        max_choices = 3
        fallback = "phan_loai_tai_san"
        empty_ok = True

    from adapter.retrievers import _template_router as tr

    importlib.reload(tr)

    mismatches = 0
    for i, q in enumerate(questions, 1):
        print(f"\n--- [{i}/{len(questions)}] {q[:80]}...")

        os.environ["RETRIEVER_V3_SINGLE_LLM"] = "0"
        importlib.reload(tr)
        t0 = time.perf_counter()
        legacy = await tr.route_and_extract(
            q,
            registry,
            classifier_prompt=classifier_prompt,
            extract_prompt_base=extract_base,
            max_choices=max_choices,
            post_process=post,
            fallback_template=fallback,
            empty_ok=empty_ok,
            legacy_classify=classify,
            legacy_extract=extract,
        )
        t_legacy = time.perf_counter() - t0

        os.environ["RETRIEVER_V3_SINGLE_LLM"] = "1"
        importlib.reload(tr)
        t0 = time.perf_counter()
        single = await tr.route_and_extract(
            q,
            registry,
            classifier_prompt=classifier_prompt,
            extract_prompt_base=extract_base,
            max_choices=max_choices,
            post_process=post,
            fallback_template=fallback,
            empty_ok=empty_ok,
            legacy_classify=classify,
            legacy_extract=extract,
        )
        t_single = time.perf_counter() - t0

        snap_l = _snapshot(legacy)
        snap_s = _snapshot(single)
        same = snap_l == snap_s
        print(f"  legacy: {t_legacy:.1f}s templates={[x['template_name'] for x in snap_l]}")
        print(f"  single: {t_single:.1f}s templates={[x['template_name'] for x in snap_s]}")
        print(f"  match: {same}")
        if not same:
            mismatches += 1
            print("  legacy:", json.dumps(snap_l, ensure_ascii=False)[:400])
            print("  single:", json.dumps(snap_s, ensure_ascii=False)[:400])

    print(f"\nDone topic={topic}: {mismatches}/{len(questions)} mismatches")
    return mismatches


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--topic",
        choices=["chia_tai_san", "tai_san", "both"],
        default="chia_tai_san",
    )
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    topics = (
        ["chia_tai_san", "tai_san"] if args.topic == "both" else [args.topic]
    )
    total = 0
    for topic in topics:
        total += asyncio.run(_run_topic(topic, args.limit, args.dry_run))
    raise SystemExit(1 if total else 0)


if __name__ == "__main__":
    main()
