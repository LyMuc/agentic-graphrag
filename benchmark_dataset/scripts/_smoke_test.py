"""
End-to-end smoke test for the benchmark/test pipeline.

Creates 2 fake "ready" rows in benchmark_grouped/smoke_test.json, runs
build_test_version then merge_test_versions on that topic, asserts the
output is correct, and cleans up everything (no leftover state).

This script does NOT touch any of your real topic files or rows.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts import _manifest  # noqa: E402
from scripts._common import (  # noqa: E402
    BENCHMARK_COLUMNS,
    BENCHMARK_GROUPED_DIR,
    EVAL_COLUMNS_TAIL,
    NESTED_COLUMNS,
    REQUIRED_FILL_COLUMNS,
    TEST_COLUMNS,
    TEST_FINAL_DIR,
    TEST_VERSIONS_DIR,
    empty_for,
    read_json,
    write_json,
)

sys.stdout.reconfigure(encoding="utf-8")

TOPIC = "smoke_test"


def _row(question: str) -> dict:
    base = {col: empty_for(col) for col in BENCHMARK_COLUMNS}
    base["question"] = question
    base["ground_truth"] = "ground truth for: " + question
    base["chu_de_phap_ly"] = TOPIC
    for col in REQUIRED_FILL_COLUMNS:
        if col in NESTED_COLUMNS:
            kind = NESTED_COLUMNS[col]
            base[col] = [f"item_{col}"] if kind is list else {f"key_{col}": f"val_{col}"}
        else:
            base[col] = f"val_{col}"
    return base


def run(cmd: list[str]) -> None:
    print(f"\n$ {' '.join(cmd)}")
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    print(res.stdout)
    if res.returncode != 0:
        print(res.stderr)
        raise RuntimeError(f"command failed: {cmd}")


def cleanup() -> None:
    p = os.path.join(BENCHMARK_GROUPED_DIR, f"{TOPIC}.json")
    if os.path.exists(p):
        os.remove(p)
    p_csv = os.path.join(BENCHMARK_GROUPED_DIR, f"{TOPIC}.csv")
    if os.path.exists(p_csv):
        os.remove(p_csv)
    tv = os.path.join(TEST_VERSIONS_DIR, TOPIC)
    if os.path.exists(tv):
        shutil.rmtree(tv)
    for ext in (".json", ".csv"):
        f = os.path.join(TEST_FINAL_DIR, f"test_final_{TOPIC}{ext}")
        if os.path.exists(f):
            os.remove(f)
    m = _manifest.load()
    if TOPIC in m["topics"]:
        del m["topics"][TOPIC]
        _manifest.save(m, with_backup=False)


def main() -> None:
    cleanup()
    try:
        os.makedirs(BENCHMARK_GROUPED_DIR, exist_ok=True)
        write_json(
            os.path.join(BENCHMARK_GROUPED_DIR, f"{TOPIC}.json"),
            [_row("smoke Q1?"), _row("smoke Q2?")],
        )
        print(f"Seeded benchmark_grouped/{TOPIC}.json with 2 ready rows.")

        run([sys.executable, "-m", "scripts.build_test_version", "--topic", TOPIC, "--date", "1705"])

        tv_dir = os.path.join(TEST_VERSIONS_DIR, TOPIC)
        files = sorted(os.listdir(tv_dir))
        assert files == [
            f"test_v1_1705_{TOPIC}.csv",
            f"test_v1_1705_{TOPIC}.json",
        ], files
        recs = read_json(os.path.join(tv_dir, f"test_v1_1705_{TOPIC}.json"))
        assert len(recs) == 2, recs
        assert list(recs[0].keys()) == TEST_COLUMNS, list(recs[0].keys())
        for c in EVAL_COLUMNS_TAIL + ["chatbot_answer"]:
            assert recs[0][c] == "", (c, recs[0][c])
        sample = recs[0]
        assert isinstance(sample["van_ban_phap_luat_lien_quan"], list), sample
        assert isinstance(sample["tinh_trang_hieu_luc"], dict), sample
        assert sample["van_ban_phap_luat_lien_quan"] == ["item_van_ban_phap_luat_lien_quan"], sample
        assert sample["tinh_trang_hieu_luc"] == {"key_tinh_trang_hieu_luc": "val_tinh_trang_hieu_luc"}, sample

        m = _manifest.load()
        assert TOPIC in m["topics"], m
        assert len(m["topics"][TOPIC]["mapped_question_ids"]) == 2
        assert len(m["topics"][TOPIC]["versions"]) == 1
        print("v1 OK: 2 rows, 22 cols, eval blanks, manifest correct.")

        run([sys.executable, "-m", "scripts.build_test_version", "--topic", TOPIC, "--date", "1705"])
        files = sorted(os.listdir(tv_dir))
        assert files == [
            f"test_v1_1705_{TOPIC}.csv",
            f"test_v1_1705_{TOPIC}.json",
        ], f"second run should NOT add files: {files}"
        print("Re-run OK: no duplicate version when nothing new.")

        write_json(
            os.path.join(BENCHMARK_GROUPED_DIR, f"{TOPIC}.json"),
            [_row("smoke Q1?"), _row("smoke Q2?"), _row("smoke Q3?")],
        )
        run([sys.executable, "-m", "scripts.build_test_version", "--topic", TOPIC, "--date", "1805"])
        files = sorted(os.listdir(tv_dir))
        assert f"test_v2_1805_{TOPIC}.json" in files, files
        recs_v2 = read_json(os.path.join(tv_dir, f"test_v2_1805_{TOPIC}.json"))
        assert len(recs_v2) == 1, recs_v2
        assert recs_v2[0]["question"] == "smoke Q3?", recs_v2
        m = _manifest.load()
        assert len(m["topics"][TOPIC]["mapped_question_ids"]) == 3
        assert len(m["topics"][TOPIC]["versions"]) == 2
        print("Incremental OK: 3rd row mapped into v2_1805 only.")

        run([sys.executable, "-m", "scripts.merge_test_versions", "--topic", TOPIC])
        out = read_json(os.path.join(TEST_FINAL_DIR, f"test_final_{TOPIC}.json"))
        assert len(out) == 3, out
        assert list(out[0].keys()) == TEST_COLUMNS, list(out[0].keys())
        questions = {r["question"] for r in out}
        assert questions == {"smoke Q1?", "smoke Q2?", "smoke Q3?"}, questions
        print("Merge OK: 3 unique rows in test_final.")

        print("\nALL SMOKE TESTS PASSED")
    finally:
        cleanup()
        print("Cleanup done. No leftover smoke test artifacts.")


if __name__ == "__main__":
    main()
