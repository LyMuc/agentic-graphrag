#!/usr/bin/env python3
"""Entity resolution: merge variant node IDs to canonical IDs in extracted JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

# variant_id -> canonical_id
ENTITY_MERGE_MAP: dict[str, str] = {
    "Một bên vợ hoặc chồng": "Vợ hoặc chồng",
    "Vợ, chồng": "Vợ chồng",
    "Tài sản chung": "Tài sản chung của vợ chồng",
    "Tài sản riêng": "Tài sản riêng của vợ, chồng",
    "Nghĩa vụ riêng về tài sản": "Nghĩa vụ riêng về tài sản của vợ, chồng",
    "Khối tài sản chung": "Khối tài sản chung của vợ chồng",
    "Khối tài sản riêng": "Khối tài sản riêng của vợ, chồng",
}


def _resolve_id(node_id: str) -> str:
    return ENTITY_MERGE_MAP.get(node_id, node_id)


def _merge_nodes(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for node in nodes:
        old_id = node.get("id", "")
        new_id = _resolve_id(old_id)
        if new_id not in merged:
            merged[new_id] = {"label": node.get("label"), "id": new_id}
        elif merged[new_id].get("label") != node.get("label"):
            # Keep first label; canonical node may appear with same label anyway.
            pass
    return list(merged.values())


def _merge_relationships(rels: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, str]] = set()
    merged: list[dict[str, Any]] = []
    for rel in rels:
        source = _resolve_id(rel.get("source_id", ""))
        target = _resolve_id(rel.get("target_id", ""))
        relationship = rel.get("relationship", "")
        key = (source, relationship, target)
        if key in seen:
            continue
        seen.add(key)
        merged.append(
            {
                "source_id": source,
                "relationship": relationship,
                "target_id": target,
            }
        )
    return merged


def merge_block(block: dict[str, Any]) -> dict[str, Any]:
    return {
        "nodes": _merge_nodes(block.get("nodes", [])),
        "relationships": _merge_relationships(block.get("relationships", [])),
    }


def merge_file(data: list[dict[str, Any]] | dict[str, Any]) -> list[dict[str, Any]]:
    blocks = data if isinstance(data, list) else [data]
    return [merge_block(block) for block in blocks]


def scan_directory(input_dir: Path) -> dict[str, Any]:
    node_hits: dict[str, list[str]] = {k: [] for k in ENTITY_MERGE_MAP}
    canonical_hits: dict[str, list[str]] = {
        v: [] for v in set(ENTITY_MERGE_MAP.values())
    }
    for path in sorted(input_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        blocks = data if isinstance(data, list) else [data]
        ids_in_file: set[str] = set()
        for block in blocks:
            for node in block.get("nodes", []):
                ids_in_file.add(node.get("id", ""))
            for rel in block.get("relationships", []):
                ids_in_file.add(rel.get("source_id", ""))
                ids_in_file.add(rel.get("target_id", ""))
        for variant, canonical in ENTITY_MERGE_MAP.items():
            if variant in ids_in_file:
                node_hits[variant].append(path.name)
        for canonical in set(ENTITY_MERGE_MAP.values()):
            if canonical in ids_in_file:
                canonical_hits[canonical].append(path.name)
    return {"variants": node_hits, "canonicals": canonical_hits}


def process_directory(input_dir: Path, dry_run: bool = False) -> dict[str, Any]:
    stats = {
        "files_processed": 0,
        "files_changed": 0,
        "replacements": {k: 0 for k in ENTITY_MERGE_MAP},
    }
    for path in sorted(input_dir.glob("*.json")):
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
        blocks = data if isinstance(data, list) else [data]

        changed = False
        for block in blocks:
            for node in block.get("nodes", []):
                old_id = node.get("id", "")
                if old_id in ENTITY_MERGE_MAP:
                    stats["replacements"][old_id] += 1
                    changed = True
            for rel in block.get("relationships", []):
                for key in ("source_id", "target_id"):
                    if rel.get(key, "") in ENTITY_MERGE_MAP:
                        changed = True

        stats["files_processed"] += 1
        if not changed:
            continue

        merged = merge_file(data)
        stats["files_changed"] += 1
        if not dry_run:
            path.write_text(
                json.dumps(merged, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("outputs/hngd_run/extracted_json"),
        help="Directory of extracted JSON files",
    )
    parser.add_argument(
        "--scan",
        action="store_true",
        help="Only scan and report variant occurrences",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report changes without writing files",
    )
    args = parser.parse_args()
    input_dir = args.input.resolve()

    if args.scan:
        report = scan_directory(input_dir)
        print(f"Scan: {input_dir}\n")
        print("Variants to merge:")
        for variant, canonical in ENTITY_MERGE_MAP.items():
            files = report["variants"][variant]
            print(f"  {variant!r} -> {canonical!r}: {len(files)} file(s)")
            for name in files:
                print(f"    - {name}")
        print("\nCanonical IDs already present:")
        for canonical, files in report["canonicals"].items():
            print(f"  {canonical!r}: {len(files)} file(s)")
        return

    stats = process_directory(input_dir, dry_run=args.dry_run)
    mode = "DRY RUN" if args.dry_run else "APPLIED"
    print(f"{mode}: {input_dir}")
    print(f"  files processed: {stats['files_processed']}")
    print(f"  files changed:   {stats['files_changed']}")
    print("  node id replacements:")
    for variant, count in stats["replacements"].items():
        if count:
            print(f"    {variant!r} -> {ENTITY_MERGE_MAP[variant]!r}: {count}")


if __name__ == "__main__":
    main()
