"""
Step 1 of the test-pipeline (MERGE-based).

Inputs (read):
  - benchmark/qa_*.json        raw question dumps (you maintain `question`,
                               `ground_truth`, `chu_de_phap_ly` here)
  - benchmark_grouped/*.json   existing per-topic working files (you
                               maintain the 8 required-fill columns here)

Output (written):
  - benchmark_grouped/<chu_de>.json + .csv

Merge rules (per question, identified by sha1(question)):
  1. Take the union of questions from BOTH sources.
  2. For EACH of the 11 canonical columns:
        - if benchmark_grouped/ has a filled value -> keep grouped value
        - else if benchmark/ has a filled value    -> copy from benchmark
        - else                                     -> empty
  3. After per-cell merge, drop rows with empty `question` or empty/invalid
     `chu_de_phap_ly`, then groupby `chu_de_phap_ly` and rewrite every
     <chu_de>.json + .csv.

Implication: anything you have already filled in benchmark_grouped/ (the
8 required-fill columns) is PROTECTED across re-runs. Adding a new
question in benchmark/ and re-running this script will append it to the
correct topic file WITHOUT touching the rows you already worked on.

Edge cases:
  - If you edit `question` text in benchmark/ AFTER having mapped it,
    its question_id changes -> the new edit becomes a "new" question and
    the old row in grouped is kept as-is. Avoid editing question text.
  - If you delete a row in benchmark/ but it still exists in
    benchmark_grouped/, the row is preserved (grouped is treated as a
    durable working store). To truly drop a question, delete it from
    benchmark_grouped/ as well.

Always creates a timestamped backup of benchmark_grouped/ before any
write.
"""

from __future__ import annotations

import os
import re
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts._common import (  # noqa: E402
    BENCHMARK_COLUMNS,
    BENCHMARK_GROUPED_DIR,
    backup_paths,
    empty_for,
    ensure_dir,
    is_filled,
    list_benchmark_files,
    normalize_columns,
    question_id,
    read_json,
    write_csv,
    write_json,
)

sys.stdout.reconfigure(encoding="utf-8")

SLUG_RE = re.compile(r"^[a-z0-9_]+$")


def _load_benchmark_dir() -> pd.DataFrame:
    files = list_benchmark_files()
    if not files:
        print("No qa_*.json files found in benchmark/.")
        return pd.DataFrame(columns=BENCHMARK_COLUMNS + ["_source_file", "_source"])

    frames: list[pd.DataFrame] = []
    for path in files:
        try:
            rows = read_json(path)
        except Exception as e:
            print(f"  WARN: cannot read {path}: {e}")
            continue
        if not rows:
            continue
        df = pd.DataFrame(rows)
        df = normalize_columns(df, BENCHMARK_COLUMNS)
        df["_source_file"] = os.path.basename(path)
        df["_source"] = "benchmark"
        frames.append(df)
        print(f"  benchmark/   {os.path.basename(path):<55} rows={len(df)}")

    if not frames:
        return pd.DataFrame(columns=BENCHMARK_COLUMNS + ["_source_file", "_source"])
    return pd.concat(frames, ignore_index=True)


def _load_grouped_dir() -> pd.DataFrame:
    if not os.path.isdir(BENCHMARK_GROUPED_DIR):
        return pd.DataFrame(columns=BENCHMARK_COLUMNS + ["_source_file", "_source"])

    frames: list[pd.DataFrame] = []
    for name in sorted(os.listdir(BENCHMARK_GROUPED_DIR)):
        if not name.endswith(".json") or name.startswith("_"):
            continue
        path = os.path.join(BENCHMARK_GROUPED_DIR, name)
        try:
            rows = read_json(path)
        except Exception as e:
            print(f"  WARN: cannot read {path}: {e}")
            continue
        if not rows:
            continue
        df = pd.DataFrame(rows)
        df = normalize_columns(df, BENCHMARK_COLUMNS)
        df["_source_file"] = name
        df["_source"] = "grouped"
        frames.append(df)
        print(f"  grouped/     {name:<55} rows={len(df)}")

    if not frames:
        return pd.DataFrame(columns=BENCHMARK_COLUMNS + ["_source_file", "_source"])
    return pd.concat(frames, ignore_index=True)


def _row_key(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["_qid"] = df["question"].apply(question_id)
    return df


def _index_by_qid(df: pd.DataFrame) -> dict[str, pd.Series]:
    if df.empty:
        return {}
    df = df.drop_duplicates("_qid", keep="first")
    return {row["_qid"]: row for _, row in df.iterrows()}


def merge_sources(df_bench: pd.DataFrame, df_grp: pd.DataFrame) -> pd.DataFrame:
    df_bench = _row_key(df_bench)
    df_grp = _row_key(df_grp)

    bench_map = _index_by_qid(df_bench)
    grp_map = _index_by_qid(df_grp)

    all_qids = set(bench_map) | set(grp_map)
    out_rows: list[dict] = []
    only_in_grouped = 0
    only_in_benchmark = 0
    in_both = 0
    for qid in all_qids:
        bn = bench_map.get(qid)
        gr = grp_map.get(qid)
        if bn is None:
            only_in_grouped += 1
        elif gr is None:
            only_in_benchmark += 1
        else:
            in_both += 1

        merged: dict = {}
        for col in BENCHMARK_COLUMNS:
            default = empty_for(col)
            gv = gr[col] if gr is not None and col in gr.index else default
            bv = bn[col] if bn is not None and col in bn.index else default
            if is_filled(gv):
                merged[col] = gv
            elif is_filled(bv):
                merged[col] = bv
            else:
                merged[col] = default

        merged["_source_file"] = (
            bn["_source_file"] if bn is not None else gr["_source_file"]
        )
        out_rows.append(merged)

    print(
        f"\nMerge summary: in_both={in_both}, only_benchmark={only_in_benchmark}, "
        f"only_grouped={only_in_grouped} (total questions={len(out_rows)})"
    )
    return pd.DataFrame(out_rows)


def drop_invalid_rows(df: pd.DataFrame) -> pd.DataFrame:
    mask_topic = df["chu_de_phap_ly"].apply(is_filled)
    dropped_no_topic = df.loc[~mask_topic, "_source_file"].value_counts().to_dict()
    df = df[mask_topic].copy()

    mask_q = df["question"].apply(is_filled)
    dropped_no_q = df.loc[~mask_q, "_source_file"].value_counts().to_dict()
    df = df[mask_q].copy()

    mask_slug = df["chu_de_phap_ly"].apply(lambda v: bool(SLUG_RE.match(str(v).strip())))
    bad_slug = df.loc[~mask_slug, ["_source_file", "chu_de_phap_ly", "question"]]
    df = df[mask_slug].copy()

    if dropped_no_topic:
        print(f"\n  WARN: {sum(dropped_no_topic.values())} row(s) dropped (no chu_de_phap_ly):")
        for f, c in dropped_no_topic.items():
            print(f"    - {f}: {c} row(s)")
    if dropped_no_q:
        print(f"  WARN: {sum(dropped_no_q.values())} row(s) dropped (no question):")
        for f, c in dropped_no_q.items():
            print(f"    - {f}: {c} row(s)")
    if not bad_slug.empty:
        print(
            f"\n  WARN: {len(bad_slug)} row(s) dropped because chu_de_phap_ly is NOT a "
            f"simple slug (must match [a-z0-9_]+). Fix these in benchmark/ then re-run:"
        )
        for _, r in bad_slug.iterrows():
            q = str(r["question"])[:70].replace("\n", " ")
            v = str(r["chu_de_phap_ly"])[:90].replace("\n", " ")
            print(f"    - file={r['_source_file']} chu_de_phap_ly={v!r} | '{q}...'")
    return df


def write_groups(df: pd.DataFrame) -> dict[str, int]:
    df = df.drop(columns=[c for c in ("_source_file",) if c in df.columns]).copy()
    counts: dict[str, int] = {}
    for topic, group in df.groupby("chu_de_phap_ly", sort=True):
        group = normalize_columns(group, BENCHMARK_COLUMNS)
        out_json = os.path.join(BENCHMARK_GROUPED_DIR, f"{topic}.json")
        out_csv = os.path.join(BENCHMARK_GROUPED_DIR, f"{topic}.csv")
        write_json(out_json, group.to_dict(orient="records"))
        write_csv(out_csv, group)
        counts[topic] = len(group)
    return counts


def _delete_stale_topic_files(active_topics: set[str]) -> list[str]:
    """Topics that no longer have any rows after a merge should not leave
    stale <chu_de>.{json,csv} files behind."""
    if not os.path.isdir(BENCHMARK_GROUPED_DIR):
        return []
    deleted: list[str] = []
    for name in os.listdir(BENCHMARK_GROUPED_DIR):
        if not name.endswith((".json", ".csv")):
            continue
        if name.startswith("_"):
            continue
        topic = os.path.splitext(name)[0]
        if topic not in active_topics:
            os.remove(os.path.join(BENCHMARK_GROUPED_DIR, name))
            deleted.append(name)
    return deleted


def main() -> None:
    print("Reading inputs...")
    df_bench = _load_benchmark_dir()
    df_grp = _load_grouped_dir()
    print(f"\nbenchmark/ rows: {len(df_bench)}")
    print(f"benchmark_grouped/ rows (existing): {len(df_grp)}")

    if df_bench.empty and df_grp.empty:
        print("Nothing to merge.")
        return

    df_merged = merge_sources(df_bench, df_grp)
    df_merged = drop_invalid_rows(df_merged)
    print(f"\nAfter validation: {len(df_merged)} row(s)")

    if os.path.exists(BENCHMARK_GROUPED_DIR):
        existing = [
            os.path.join(BENCHMARK_GROUPED_DIR, n)
            for n in os.listdir(BENCHMARK_GROUPED_DIR)
            if not n.startswith("_")
        ]
        if existing:
            folder = backup_paths(existing, "build_grouped")
            if folder:
                print(f"\nBacked up existing grouped/ to: {folder}")

    ensure_dir(BENCHMARK_GROUPED_DIR)
    counts = write_groups(df_merged)
    deleted = _delete_stale_topic_files(set(counts))

    print(f"\nWrote {len(counts)} topic file pair(s) to: benchmark_grouped/")
    for topic in sorted(counts):
        print(f"  {topic:<45} {counts[topic]:>5} row(s)")
    print(f"\nGrand total: {sum(counts.values())} row(s) across {len(counts)} topic(s).")
    if deleted:
        print(f"\nRemoved {len(deleted)} stale file(s) (topic had no rows): {deleted}")


if __name__ == "__main__":
    main()
