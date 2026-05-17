"""
Normalize every qa_*.{json,csv} file in benchmark/ to the canonical
11-column benchmark schema (BENCHMARK_COLUMNS in _common.py).

This script REPLACES the old benchmark/cleanup_columns.py.

Why a replacement:
  cleanup_columns.py read CSV, dropped columns, then regenerated JSON from
  CSV - which silently wiped any edits the user had made directly in JSON.
  This script instead reads each file in its OWN format, normalizes the
  column set, and writes BOTH CSV and JSON back in sync.

Default behaviour (no args): process every qa_*.{json,csv} in benchmark/.
Use --files <name1> <name2> ... to target specific files (without folder
prefix; either .json or .csv suffix works).

Always creates a timestamped backup in _state/backups/ before any write.
"""

from __future__ import annotations

import argparse
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts._common import (  # noqa: E402
    BENCHMARK_COLUMNS,
    BENCHMARK_DIR,
    backup_paths,
    is_filled,
    normalize_columns,
    read_json,
    write_csv,
    write_json,
)

sys.stdout.reconfigure(encoding="utf-8")


def discover_pairs(filter_names: list[str] | None) -> list[tuple[str, str]]:
    """Return list of (json_path, csv_path) for each qa_* base name in
    benchmark/. At least one of the two paths must exist for that base."""
    bases: dict[str, dict[str, str]] = {}
    for name in os.listdir(BENCHMARK_DIR):
        if not name.startswith("qa_"):
            continue
        if not (name.endswith(".json") or name.endswith(".csv")):
            continue
        base, ext = os.path.splitext(name)
        bases.setdefault(base, {})[ext] = os.path.join(BENCHMARK_DIR, name)

    if filter_names:
        wanted = {os.path.splitext(n)[0] for n in filter_names}
        bases = {b: v for b, v in bases.items() if b in wanted}

    return [
        (v.get(".json", os.path.join(BENCHMARK_DIR, b + ".json")),
         v.get(".csv", os.path.join(BENCHMARK_DIR, b + ".csv")))
        for b, v in sorted(bases.items())
    ]


def load_records(json_path: str, csv_path: str) -> pd.DataFrame:
    """Prefer the source that has the richer 'filled' content for the 11
    canonical columns. Tie -> JSON wins (user usually edits JSON).

    Both sources are normalized first so that nested columns (list/dict)
    are properly typed before we compare filled-cell counts.
    """
    df_json = None
    df_csv = None
    if os.path.exists(json_path):
        try:
            df_json = pd.DataFrame(read_json(json_path))
            df_json = normalize_columns(df_json, BENCHMARK_COLUMNS)
        except Exception as e:
            print(f"  WARN: cannot read JSON {json_path}: {e}")
    if os.path.exists(csv_path):
        try:
            df_csv = pd.read_csv(csv_path)
            df_csv = normalize_columns(df_csv, BENCHMARK_COLUMNS)
        except Exception as e:
            print(f"  WARN: cannot read CSV {csv_path}: {e}")

    if df_json is None and df_csv is None:
        return pd.DataFrame(columns=BENCHMARK_COLUMNS)
    if df_json is None:
        return df_csv
    if df_csv is None:
        return df_json

    def filled_score(df: pd.DataFrame) -> int:
        score = 0
        for col in BENCHMARK_COLUMNS:
            if col in df.columns:
                score += int(df[col].apply(is_filled).sum())
        return score

    return df_json if filled_score(df_json) >= filled_score(df_csv) else df_csv


def normalize_one(json_path: str, csv_path: str) -> dict:
    base_name = os.path.splitext(os.path.basename(json_path))[0]
    df = load_records(json_path, csv_path)

    before_cols = list(df.columns)
    df_norm = normalize_columns(df, BENCHMARK_COLUMNS)

    write_json(json_path, df_norm.to_dict(orient="records"))
    write_csv(csv_path, df_norm)

    return {
        "file": base_name,
        "rows": len(df_norm),
        "before_cols": before_cols,
        "after_cols": list(df_norm.columns),
        "dropped": [c for c in before_cols if c not in BENCHMARK_COLUMNS],
        "added": [c for c in BENCHMARK_COLUMNS if c not in before_cols],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--files",
        nargs="*",
        default=None,
        help="Specific qa_* file base-names to process (default: ALL).",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip the safety backup (NOT recommended).",
    )
    args = parser.parse_args()

    pairs = discover_pairs(args.files)
    if not pairs:
        print("No matching files in benchmark/. Nothing to do.")
        return

    if not args.no_backup:
        backup_folder = backup_paths(
            [p for pair in pairs for p in pair],
            reason="normalize_benchmark",
        )
        if backup_folder:
            print(f"Backup created at: {backup_folder}\n")

    print(f"Normalizing {len(pairs)} file pair(s) to {len(BENCHMARK_COLUMNS)} canonical columns\n")
    for json_path, csv_path in pairs:
        print(f"-> {os.path.basename(json_path)}")
        info = normalize_one(json_path, csv_path)
        print(f"   rows={info['rows']}, dropped={info['dropped']}, added={info['added']}")

    print("\nDone.")


if __name__ == "__main__":
    main()
