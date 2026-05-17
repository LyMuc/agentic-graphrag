"""
Smoke test for build_grouped_benchmark.py merge logic.

Verifies:
  1. New question added to benchmark/ appears in benchmark_grouped/.
  2. Cells filled by the user in benchmark_grouped/ are PRESERVED when
     the same question is re-emitted by Script 1.
  3. A question whose `chu_de_phap_ly` is changed in benchmark_grouped/
     moves to the new topic file on next run (grouped wins per cell).
  4. The smoke fixture is fully cleaned up (no leftover artifacts).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts._common import (  # noqa: E402
    BENCHMARK_COLUMNS,
    BENCHMARK_DIR,
    BENCHMARK_GROUPED_DIR,
    empty_for,
    read_json,
    write_json,
)

sys.stdout.reconfigure(encoding="utf-8")

SMOKE_BENCHMARK = os.path.join(BENCHMARK_DIR, "qa_zzz_smoke_merge.json")
SMOKE_BENCHMARK_CSV = os.path.join(BENCHMARK_DIR, "qa_zzz_smoke_merge.csv")
TOPIC_A = "zzz_smoke_topic_a"
TOPIC_B = "zzz_smoke_topic_b"
TOPIC_FILES = [
    os.path.join(BENCHMARK_GROUPED_DIR, f"{t}{ext}")
    for t in (TOPIC_A, TOPIC_B)
    for ext in (".json", ".csv")
]


def _make_row(q: str, topic: str = TOPIC_A) -> dict:
    base = {col: empty_for(col) for col in BENCHMARK_COLUMNS}
    base["question"] = q
    base["ground_truth"] = f"GT: {q}"
    base["chu_de_phap_ly"] = topic
    return base


def _run_script1() -> None:
    print("\n$ python -m scripts.build_grouped_benchmark")
    r = subprocess.run(
        [sys.executable, "-m", "scripts.build_grouped_benchmark"],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if r.returncode != 0:
        print(r.stdout)
        print(r.stderr)
        raise RuntimeError("Script 1 failed")
    # show only the last lines so we don't drown in real-data logs
    tail = "\n".join(r.stdout.splitlines()[-20:])
    print(tail)


def cleanup() -> None:
    for p in (SMOKE_BENCHMARK, SMOKE_BENCHMARK_CSV, *TOPIC_FILES):
        if os.path.exists(p):
            os.remove(p)


def main() -> None:
    cleanup()
    try:
        write_json(SMOKE_BENCHMARK, [_make_row("smoke_merge Q1?"), _make_row("smoke_merge Q2?")])
        print("Seeded benchmark/qa__smoke_merge.json with 2 rows (topic_a).")

        _run_script1()
        grp = read_json(os.path.join(BENCHMARK_GROUPED_DIR, f"{TOPIC_A}.json"))
        qs = {r["question"] for r in grp}
        assert qs == {"smoke_merge Q1?", "smoke_merge Q2?"}, qs
        print(f"Step 1 OK: topic_a has 2 rows after first Script 1 run.")

        grp = read_json(os.path.join(BENCHMARK_GROUPED_DIR, f"{TOPIC_A}.json"))
        for r in grp:
            if r["question"] == "smoke_merge Q1?":
                r["loai_cau_hoi"] = "USER_FILLED"
                r["can_cu_phap_ly_chinh"] = ["Dieu 8"]
                r["tinh_trang_hieu_luc"] = {"Dieu 8": "CON_HIEU_LUC"}
        write_json(os.path.join(BENCHMARK_GROUPED_DIR, f"{TOPIC_A}.json"), grp)
        print("User edit applied: filled scalar + list + dict cells of Q1 in grouped/topic_a.json")

        write_json(
            SMOKE_BENCHMARK,
            [_make_row("smoke_merge Q1?"), _make_row("smoke_merge Q2?"), _make_row("smoke_merge Q3?")],
        )
        print("Added smoke_merge Q3? to benchmark/qa__smoke_merge.json (still only chu_de_phap_ly).")

        _run_script1()
        grp = read_json(os.path.join(BENCHMARK_GROUPED_DIR, f"{TOPIC_A}.json"))
        assert len(grp) == 3, grp
        q1 = next(r for r in grp if r["question"] == "smoke_merge Q1?")
        q3 = next(r for r in grp if r["question"] == "smoke_merge Q3?")
        assert q1["loai_cau_hoi"] == "USER_FILLED", f"Q1 lost user edit: {q1}"
        assert q1["can_cu_phap_ly_chinh"] == ["Dieu 8"], q1
        assert q1["tinh_trang_hieu_luc"] == {"Dieu 8": "CON_HIEU_LUC"}, q1
        assert isinstance(q1["can_cu_phap_ly_chinh"], list), q1
        assert isinstance(q1["tinh_trang_hieu_luc"], dict), q1
        assert q3["loai_cau_hoi"] == "", q3
        assert q3["can_cu_phap_ly_chinh"] == [], q3
        assert q3["tinh_trang_hieu_luc"] == {}, q3
        print("Step 2 OK: Q1 nested user edits PRESERVED as native list/dict, Q3 default empty.")

        grp = read_json(os.path.join(BENCHMARK_GROUPED_DIR, f"{TOPIC_A}.json"))
        for r in grp:
            if r["question"] == "smoke_merge Q2?":
                r["chu_de_phap_ly"] = TOPIC_B
        write_json(os.path.join(BENCHMARK_GROUPED_DIR, f"{TOPIC_A}.json"), grp)
        print(f"User edit applied: moved Q2 from {TOPIC_A} -> {TOPIC_B} in grouped.")

        _run_script1()
        grp_a = read_json(os.path.join(BENCHMARK_GROUPED_DIR, f"{TOPIC_A}.json"))
        grp_b = read_json(os.path.join(BENCHMARK_GROUPED_DIR, f"{TOPIC_B}.json"))
        a_questions = {r["question"] for r in grp_a}
        b_questions = {r["question"] for r in grp_b}
        assert "smoke_merge Q2?" not in a_questions, a_questions
        assert b_questions == {"smoke_merge Q2?"}, b_questions
        print("Step 3 OK: Q2 moved to topic_b, topic_a no longer contains it.")

        print("\nALL MERGE SMOKE TESTS PASSED")
    finally:
        cleanup()
        print("Cleanup done.")


if __name__ == "__main__":
    main()
