"""
Step 3 of the test-pipeline.

For each topic, concatenate every test_v*_<chu_de>.json under
test_versions/<chu_de>/, deduplicate by `question_id`, KEEPING the
NEWEST occurrence (so later edits override earlier ones), and write
the merged result to test_final/test_final_<chu_de>.{json,csv}.

CLI:
  python -m scripts.merge_test_versions
  python -m scripts.merge_test_versions --topic dieu_kien_ket_hon
"""

from __future__ import annotations

import argparse
import os
import re
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts._common import (  # noqa: E402
    TEST_COLUMNS,
    TEST_FINAL_DIR,
    TEST_VERSIONS_DIR,
    backup_paths,
    ensure_dir,
    normalize_columns,
    question_id,
    read_json,
    write_csv,
    write_json,
)

sys.stdout.reconfigure(encoding="utf-8")

# Matches "test_v<version>_<date>_<topic>.json"
FILE_RE = re.compile(r"^test_v(\d+)_(\d{4})_(?P<topic>.+)\.json$")


def list_topics() -> list[str]:
    if not os.path.isdir(TEST_VERSIONS_DIR):
        return []
    return sorted(
        d for d in os.listdir(TEST_VERSIONS_DIR)
        if os.path.isdir(os.path.join(TEST_VERSIONS_DIR, d))
    )


def list_version_files(topic: str) -> list[tuple[int, str]]:
    """Return [(version_number, json_path), ...] sorted by version asc."""
    folder = os.path.join(TEST_VERSIONS_DIR, topic)
    if not os.path.isdir(folder):
        return []
    out: list[tuple[int, str]] = []
    for name in os.listdir(folder):
        m = FILE_RE.match(name)
        if not m:
            continue
        if m.group("topic") != topic:
            continue
        out.append((int(m.group(1)), os.path.join(folder, name)))
    out.sort(key=lambda x: x[0])
    return out


def merge_topic(topic: str) -> dict:
    version_files = list_version_files(topic)
    if not version_files:
        return {"topic": topic, "skipped": True, "reason": "no version files"}

    frames: list[pd.DataFrame] = []
    for version, path in version_files:
        rows = read_json(path)
        if not rows:
            continue
        df = pd.DataFrame(rows)
        df["_version"] = version
        df["_qid"] = df["question"].apply(question_id)
        frames.append(df)

    if not frames:
        return {"topic": topic, "skipped": True, "reason": "all version files empty"}

    big = pd.concat(frames, ignore_index=True)
    before = len(big)
    big.sort_values("_version", kind="mergesort", inplace=True)
    big = big.drop_duplicates(subset="_qid", keep="last").copy()
    after = len(big)

    big.drop(columns=["_version", "_qid"], inplace=True)
    big = normalize_columns(big, TEST_COLUMNS)

    out_json = os.path.join(TEST_FINAL_DIR, f"test_final_{topic}.json")
    out_csv = os.path.join(TEST_FINAL_DIR, f"test_final_{topic}.csv")
    backup_paths([out_json, out_csv], "merge_final")
    write_json(out_json, big.to_dict(orient="records"))
    write_csv(out_csv, big)

    return {
        "topic": topic,
        "versions_merged": len(version_files),
        "rows_before_dedup": before,
        "rows_after_dedup": after,
        "out_json": out_json,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--topic",
        default=None,
        help="Only merge this single topic (default: all topics).",
    )
    args = parser.parse_args()

    topics = [args.topic] if args.topic else list_topics()
    if not topics:
        print("No topics found in test_versions/.")
        return

    ensure_dir(TEST_FINAL_DIR)

    print(f"Merging {len(topics)} topic(s) into test_final/\n")
    results: list[dict] = []
    for topic in topics:
        res = merge_topic(topic)
        results.append(res)
        if res.get("skipped"):
            print(f"-> {topic}: SKIP ({res['reason']})")
        else:
            print(
                f"-> {topic}: merged {res['versions_merged']} version(s), "
                f"{res['rows_before_dedup']} -> {res['rows_after_dedup']} rows after dedup"
            )

    print("\nDone.")


if __name__ == "__main__":
    main()
