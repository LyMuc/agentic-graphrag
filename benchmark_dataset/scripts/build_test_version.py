"""
Step 2 of the test-pipeline.

For each topic in benchmark_grouped/, find rows that are NEWLY ready
(all 8 required-fill columns are non-empty) AND not yet mapped (their
question_id is absent from the manifest). Emit ONE new test-version
file per topic with only those new rows, then update the manifest.

Output file name:
  test_versions/<chu_de>/test_v<N>_<DDMM>_<chu_de>.json (+ .csv)

CLI:
  python -m scripts.build_test_version                     # all topics
  python -m scripts.build_test_version --topic dieu_kien_ket_hon
  python -m scripts.build_test_version --date 1805         # override date
  python -m scripts.build_test_version --dry-run           # preview only

Manifest updates are atomic (tmp + rename) and backed up before each
write. If --dry-run is passed, no files are written and the manifest
is left untouched.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts import _manifest  # noqa: E402
from scripts._common import (  # noqa: E402
    BENCHMARK_GROUPED_DIR,
    PACKAGE_DIR,
    REQUIRED_FILL_COLUMNS,
    TEST_COLUMNS,
    TEST_VERSIONS_DIR,
    ensure_dir,
    is_filled,
    normalize_columns,
    question_id,
    read_json,
    write_csv,
    write_json,
)

sys.stdout.reconfigure(encoding="utf-8")


def is_ready_row(row: pd.Series) -> bool:
    return all(is_filled(row.get(col)) for col in REQUIRED_FILL_COLUMNS)


def list_grouped_topics() -> list[str]:
    if not os.path.isdir(BENCHMARK_GROUPED_DIR):
        return []
    return sorted(
        os.path.splitext(n)[0]
        for n in os.listdir(BENCHMARK_GROUPED_DIR)
        if n.endswith(".json")
    )


def select_new_rows(
    topic: str,
    manifest: dict,
) -> tuple[pd.DataFrame, list[str]]:
    """Return (df_new_rows_with_qid_col, list_of_ids_to_record)."""
    src = os.path.join(BENCHMARK_GROUPED_DIR, f"{topic}.json")
    if not os.path.exists(src):
        return pd.DataFrame(), []

    df = pd.DataFrame(read_json(src))
    if df.empty:
        return pd.DataFrame(), []

    df["_qid"] = df["question"].apply(question_id)
    df["_ready"] = df.apply(is_ready_row, axis=1)

    already = set(_manifest.topic_entry(manifest, topic)["mapped_question_ids"])
    mask = df["_ready"] & (~df["_qid"].isin(already))
    new_df = df[mask].copy()
    return new_df, new_df["_qid"].tolist()


def build_test_dataframe(new_df: pd.DataFrame) -> pd.DataFrame:
    """Project new_df onto the TEST_COLUMNS schema (eval cols become '')."""
    df = new_df.drop(columns=[c for c in ("_qid", "_ready") if c in new_df.columns])
    return normalize_columns(df, TEST_COLUMNS)


def write_test_version(
    topic: str,
    version: int,
    date_tag: str,
    df: pd.DataFrame,
) -> tuple[str, str]:
    folder = os.path.join(TEST_VERSIONS_DIR, topic)
    ensure_dir(folder)
    base = f"test_v{version}_{date_tag}_{topic}"
    json_path = os.path.join(folder, base + ".json")
    csv_path = os.path.join(folder, base + ".csv")
    write_json(json_path, df.to_dict(orient="records"))
    write_csv(csv_path, df)
    return json_path, csv_path


def rel(path: str) -> str:
    return os.path.relpath(path, PACKAGE_DIR).replace("\\", "/")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--topic",
        default=None,
        help="Only process this single topic (default: all topics).",
    )
    parser.add_argument(
        "--date",
        default=None,
        help="DDMM date tag for the file name (default: today).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what WOULD be mapped without writing anything.",
    )
    args = parser.parse_args()

    date_tag = args.date or datetime.now().strftime("%d%m")
    if len(date_tag) != 4 or not date_tag.isdigit():
        parser.error(f"--date must be DDMM (4 digits), got: {date_tag!r}")

    topics = [args.topic] if args.topic else list_grouped_topics()
    if not topics:
        print(
            "No topic files found in benchmark_grouped/. "
            "Run scripts.build_grouped_benchmark first."
        )
        return

    manifest = _manifest.load()
    any_changes = False
    summary: list[tuple[str, int, int]] = []

    for topic in topics:
        new_df, new_ids = select_new_rows(topic, manifest)
        topic_obj = _manifest.topic_entry(manifest, topic)
        total_already = len(topic_obj["mapped_question_ids"])

        if new_df.empty:
            print(f"-> {topic}: 0 new ready rows (already mapped: {total_already}).")
            summary.append((topic, 0, total_already))
            continue

        version = _manifest.next_version_number(topic_obj)
        out_df = build_test_dataframe(new_df)

        if args.dry_run:
            print(
                f"-> {topic}: would emit v{version}_{date_tag} with {len(out_df)} new row(s) "
                f"(currently mapped: {total_already})."
            )
            summary.append((topic, len(out_df), total_already))
            continue

        json_path, csv_path = write_test_version(topic, version, date_tag, out_df)
        topic_obj["mapped_question_ids"].extend(new_ids)
        topic_obj["versions"].append(
            {
                "version": version,
                "date": date_tag,
                "files": [rel(json_path), rel(csv_path)],
                "added_question_ids": new_ids,
            }
        )
        any_changes = True
        print(
            f"-> {topic}: wrote v{version}_{date_tag} with {len(out_df)} new row(s); "
            f"manifest now tracks {total_already + len(new_ids)}."
        )
        summary.append((topic, len(out_df), total_already + len(new_ids)))

    if any_changes and not args.dry_run:
        _manifest.save(manifest)
        print(f"\nManifest updated: {rel(_manifest.MANIFEST_PATH)}")
    elif args.dry_run:
        print("\n(dry-run: no files written, manifest unchanged)")
    else:
        print("\nNothing to do.")

    if summary:
        print("\nSummary:")
        print(f"  {'topic':<45} {'new':>6} {'total mapped':>14}")
        for t, n, total in summary:
            print(f"  {t:<45} {n:>6} {total:>14}")


if __name__ == "__main__":
    main()
