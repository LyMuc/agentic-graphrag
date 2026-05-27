#!/usr/bin/env python3
"""Post-filter extracted triple JSON files.

Removes:
- Invalid head_type/relation/tail_type pairs (schema violations)
- Triples anchored to the wrong LegalProvision (few-shot / cross-article leakage)
- Orphan triples not connected to the current record

Usage:
    python scripts/filter_extracted_triples.py \\
        --input outputs/che_do_tai_san_cua_vo_chong/extracted_json \\
        --in-place
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kgb.builder.validation import is_valid_hngd_relation_pair


def _triple_key(triple: dict[str, Any]) -> tuple[Any, ...]:
    return (
        triple.get("head"),
        triple.get("head_type"),
        triple.get("relation"),
        triple.get("tail"),
        triple.get("tail_type"),
        triple.get("inference"),
    )


_CANONICAL_ASSET_ALIASES: tuple[tuple[str, str], ...] = (
    ("tài sản chung", "Tài sản chung"),
    ("tài sản riêng", "Tài sản riêng"),
)


def _add_canonical_asset_aliases(grounded: set[str]) -> None:
    """Bridge naming variants like 'Tài sản chung của vợ chồng' -> 'Tài sản chung'."""
    for entity in list(grounded):
        lowered = entity.casefold()
        for pattern, canonical in _CANONICAL_ASSET_ALIASES:
            if pattern in lowered:
                grounded.add(canonical)


def _expand_grounded_entities(
    triples: list[dict[str, Any]],
    record_id: str,
) -> set[str]:
    """Entities connected to the current record through the triple graph."""
    grounded: set[str] = {record_id}

    for triple in triples:
        if triple.get("relation") == "BASED_ON" and triple.get("tail") == record_id:
            head = triple.get("head", "")
            if head:
                grounded.add(head)

    _add_canonical_asset_aliases(grounded)

    changed = True
    while changed:
        changed = False
        for triple in triples:
            head = triple.get("head", "")
            tail = triple.get("tail", "")
            relation = triple.get("relation", "")

            if relation == "REFERENCE_TO" and head == record_id:
                for node in (head, tail):
                    if node and node not in grounded:
                        grounded.add(node)
                        changed = True
                continue

            if head in grounded and tail and tail not in grounded:
                grounded.add(tail)
                changed = True
            elif tail in grounded and head and head not in grounded:
                grounded.add(head)
                changed = True

        before = len(grounded)
        _add_canonical_asset_aliases(grounded)
        if len(grounded) > before:
            changed = True

    return grounded


def filter_triples_for_record(
    triples: list[dict[str, Any]],
    record_id: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
    """Return (kept, removed, reason_counts) for a single record."""
    removed: list[dict[str, Any]] = []
    reason_counts = {
        "invalid_relation_pair": 0,
        "wrong_anchor": 0,
        "orphan": 0,
        "duplicate": 0,
    }
    structurally_kept: list[dict[str, Any]] = []

    for triple in triples:
        relation = triple.get("relation", "")
        head = triple.get("head", "")
        tail = triple.get("tail", "")
        head_type = triple.get("head_type", "")
        tail_type = triple.get("tail_type", "")

        if not is_valid_hngd_relation_pair(relation, head_type, tail_type):
            removed.append(triple)
            reason_counts["invalid_relation_pair"] += 1
            continue

        if relation == "REFERENCE_TO":
            if head_type == "LegalProvision" and head != record_id:
                removed.append(triple)
                reason_counts["wrong_anchor"] += 1
                continue

        if relation == "BASED_ON" and tail_type == "LegalProvision":
            if tail != record_id:
                removed.append(triple)
                reason_counts["wrong_anchor"] += 1
                continue

        if head_type == "LegalProvision" and head != record_id:
            removed.append(triple)
            reason_counts["wrong_anchor"] += 1
            continue

        structurally_kept.append(triple)

    grounded = _expand_grounded_entities(structurally_kept, record_id)
    kept: list[dict[str, Any]] = []
    for triple in structurally_kept:
        head = triple.get("head", "")
        tail = triple.get("tail", "")
        if head in grounded and tail in grounded:
            kept.append(triple)
        else:
            removed.append(triple)
            reason_counts["orphan"] += 1

    deduped: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for triple in kept:
        key = _triple_key(triple)
        if key in seen:
            removed.append(triple)
            reason_counts["duplicate"] += 1
            continue
        seen.add(key)
        deduped.append(triple)

    return deduped, removed, reason_counts


def process_directory(
    input_dir: Path,
    output_dir: Path | None,
    in_place: bool,
) -> dict[str, Any]:
    if not input_dir.is_dir():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")

    if in_place:
        target_dir = input_dir
    elif output_dir is not None:
        target_dir = output_dir
        target_dir.mkdir(parents=True, exist_ok=True)
    else:
        target_dir = input_dir

    summary: dict[str, Any] = {
        "input_dir": str(input_dir),
        "output_dir": str(target_dir),
        "files_processed": 0,
        "triples_before": 0,
        "triples_after": 0,
        "triples_removed": 0,
        "reason_totals": {
            "invalid_relation_pair": 0,
            "wrong_anchor": 0,
            "orphan": 0,
            "duplicate": 0,
        },
        "per_file": [],
    }

    for json_path in sorted(input_dir.glob("*.json")):
        record_id = json_path.stem
        with open(json_path, encoding="utf-8") as f:
            triples = json.load(f)

        if not isinstance(triples, list):
            print(f"SKIP {json_path.name}: expected JSON array", file=sys.stderr)
            continue

        kept, removed, reason_counts = filter_triples_for_record(triples, record_id)
        out_path = target_dir / json_path.name

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(kept, f, ensure_ascii=False, indent=2)

        summary["files_processed"] += 1
        summary["triples_before"] += len(triples)
        summary["triples_after"] += len(kept)
        summary["triples_removed"] += len(removed)
        for key, value in reason_counts.items():
            summary["reason_totals"][key] += value
        summary["per_file"].append(
            {
                "record_id": record_id,
                "before": len(triples),
                "after": len(kept),
                "removed": len(removed),
                **reason_counts,
            }
        )

        if removed:
            print(
                f"{record_id}: {len(triples)} -> {len(kept)} "
                f"(schema={reason_counts['invalid_relation_pair']}, "
                f"anchor={reason_counts['wrong_anchor']}, "
                f"orphan={reason_counts['orphan']})"
            )

    return summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Filter invalid/leaked triples from extracted JSON files."
    )
    parser.add_argument(
        "--input",
        "-i",
        required=True,
        type=Path,
        help="Directory containing extracted JSON files",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Output directory (default: same as input unless --in-place)",
    )
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Overwrite files in the input directory",
    )
    args = parser.parse_args()

    if args.in_place and args.output is not None:
        parser.error("Use either --in-place or --output, not both.")

    summary = process_directory(args.input, args.output, args.in_place)

    totals = summary["reason_totals"]
    print(
        f"\nDone: {summary['files_processed']} files | "
        f"{summary['triples_before']} -> {summary['triples_after']} triples "
        f"({summary['triples_removed']} removed)"
    )
    print(
        "Removed by reason: "
        f"schema={totals['invalid_relation_pair']}, "
        f"anchor={totals['wrong_anchor']}, "
        f"orphan={totals['orphan']}, "
        f"duplicate={totals['duplicate']}"
    )


if __name__ == "__main__":
    main()
