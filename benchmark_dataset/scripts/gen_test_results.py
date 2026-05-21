"""
Aggregate benchmark test-version JSON files into per-topic and overall result JSON.

For each test file like:
  test_versions/cap_duong/test_v1_1705_cap_duong.json

Writes:
  test_versions/cap_duong/test_v1_1705_cap_duong_result.json

And a combined summary (only rows with chatbot_answer filled):
  result/result_v1_1705.json

CLI:
  python -m benchmark_dataset.scripts.gen_test_results
  python -m benchmark_dataset.scripts.gen_test_results --version 1 --date 1705
  python -m benchmark_dataset.scripts.gen_test_results benchmark_dataset/test_versions/cap_duong/test_v1_1705_cap_duong.json
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts._common import (  # noqa: E402
    PACKAGE_DIR,
    TEST_VERSIONS_DIR,
    is_filled,
    read_json,
    write_json,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

RESULT_DIR = os.path.join(PACKAGE_DIR, "result")

FILE_RE = re.compile(r"^test_v(?P<version>\d+)_(?P<date>\d{4})_(?P<topic>.+)\.json$")
RESULT_FILE_RE = re.compile(r"^test_v\d+_\d{4}_.+_result\.json$")


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    if s == "" or s.lower() == "nan":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _to_int(value: Any) -> int | None:
    f = _to_float(value)
    if f is None:
        return None
    return int(f)


def _round(value: float | None, digits: int = 4) -> float | None:
    if value is None:
        return None
    return round(value, digits)


def _count_question_type(rows: list[dict], loai: str) -> int:
    return sum(1 for row in rows if str(row.get("loai_cau_hoi", "")).strip() == loai)


def _answered_rows(rows: list[dict]) -> list[dict]:
    """Keep only rows that already have a chatbot_answer."""
    return [row for row in rows if is_filled(row.get("chatbot_answer"))]


def _has_invalid_citation(row: dict) -> bool:
    co_loi = _to_float(row.get("co_loi_hieu_luc"))
    if co_loi is not None and co_loi > 0:
        return True

    valid = _to_int(row.get("so_can_cu_con_hieu_luc"))
    total = _to_int(row.get("tong_so_can_cu_duoc_neu_ra"))
    if valid is None or total is None:
        return False
    return valid < total


def aggregate_rows(rows: list[dict], *, chu_de_phap_ly: str | None = None) -> dict:
    so_cau_hoi = len(rows)
    lca_values = [_to_float(r.get("legal_citation_accuracy")) for r in rows]
    cpa_values = [_to_float(r.get("citation_prioritization_accuracy")) for r in rows]

    valid_citations = 0
    total_citations = 0
    for row in rows:
        valid = _to_int(row.get("so_can_cu_con_hieu_luc"))
        total = _to_int(row.get("tong_so_can_cu_duoc_neu_ra"))
        if valid is not None:
            valid_citations += valid
        if total is not None:
            total_citations += total

    lca_scored = [v for v in lca_values if v is not None]
    cpa_scored = [v for v in cpa_values if v is not None]
    invalid_count = sum(1 for row in rows if _has_invalid_citation(row))

    out: dict[str, Any] = {
        "so_cau_hoi": so_cau_hoi,
        "cau_hoi_ly_thuyet": _count_question_type(rows, "Lý thuyết"),
        "cau_hoi_tinh_huong": _count_question_type(rows, "Tình huống"),
        "legal_citation_accuracy": _round(sum(lca_scored) / len(lca_scored)) if lca_scored else None,
        "legal_validity_accuracy": _round(valid_citations / total_citations)
        if total_citations
        else None,
        "citation_prioritization_accuracy": _round(sum(cpa_scored) / len(cpa_scored))
        if cpa_scored
        else None,
        "invalid_citation_rate": _round(invalid_count / so_cau_hoi) if so_cau_hoi else None,
    }

    if chu_de_phap_ly is not None:
        out = {"chu_de_phap_ly": chu_de_phap_ly, **out}

    return out


def list_test_files(
    root: str,
    *,
    version: int | None = None,
    date: str | None = None,
) -> list[str]:
    out: list[str] = []
    for dirpath, _, names in os.walk(root):
        for name in sorted(names):
            if RESULT_FILE_RE.match(name):
                continue
            m = FILE_RE.match(name)
            if not m:
                continue
            if version is not None and int(m.group("version")) != version:
                continue
            if date is not None and m.group("date") != date:
                continue
            out.append(os.path.join(dirpath, name))
    return sorted(out)


def result_path_for_test(test_path: str) -> str:
    base, ext = os.path.splitext(test_path)
    return f"{base}_result{ext}"


def parse_test_meta(path: str) -> tuple[int, str, str]:
    name = os.path.basename(path)
    m = FILE_RE.match(name)
    if not m:
        raise ValueError(f"Not a test-version file: {path}")
    return int(m.group("version")), m.group("date"), m.group("topic")


def generate_for_test_file(test_path: str) -> dict:
    version, date, topic = parse_test_meta(test_path)
    rows = read_json(test_path)
    chu_de = str(rows[0].get("chu_de_phap_ly") or topic) if rows else topic
    result = aggregate_rows(rows, chu_de_phap_ly=chu_de)
    out_path = result_path_for_test(test_path)
    write_json(out_path, [result])
    return {
        "test_path": test_path,
        "result_path": out_path,
        "version": version,
        "date": date,
        "topic": topic,
        "rows": rows,
        "result": result,
    }


def generate_overall_result(items: list[dict], *, version: int, date: str) -> tuple[str, dict]:
    all_rows: list[dict] = []
    for item in items:
        all_rows.extend(item["rows"])

    answered = _answered_rows(all_rows)
    result = aggregate_rows(answered)
    out_path = os.path.join(RESULT_DIR, f"result_v{version}_{date}.json")
    write_json(out_path, [result])
    meta = {
        "out_path": out_path,
        "total_rows": len(all_rows),
        "answered_rows": len(answered),
        "skipped_rows": len(all_rows) - len(answered),
        "result": result,
    }
    return out_path, meta


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths",
        nargs="*",
        help="Specific test JSON file(s). Default: scan all under test_versions/.",
    )
    parser.add_argument("--version", type=int, default=None, help="Filter by version number, e.g. 1")
    parser.add_argument("--date", default=None, help="Filter by date tag, e.g. 1705")
    args = parser.parse_args()

    if args.paths:
        test_files = [os.path.abspath(p) for p in args.paths]
    else:
        test_files = list_test_files(TEST_VERSIONS_DIR, version=args.version, date=args.date)

    if not test_files:
        print("No test-version JSON files found.")
        return

    os.makedirs(RESULT_DIR, exist_ok=True)

    grouped: dict[tuple[int, str], list[dict]] = {}
    for test_path in test_files:
        item = generate_for_test_file(test_path)
        key = (item["version"], item["date"])
        grouped.setdefault(key, []).append(item)
        r = item["result"]
        print(
            f"-> {item['topic']}: {item['result_path']} "
            f"(n={r['so_cau_hoi']}, LCA={r['legal_citation_accuracy']}, "
            f"LVA={r['legal_validity_accuracy']}, ICR={r['invalid_citation_rate']})"
        )

    for (version, date), items in sorted(grouped.items()):
        overall_path, meta = generate_overall_result(items, version=version, date=date)
        r = meta["result"]
        print(
            f"\nOverall: {overall_path} "
            f"(answered={meta['answered_rows']}/{meta['total_rows']}, "
            f"skipped={meta['skipped_rows']}, LCA={r['legal_citation_accuracy']}, "
            f"LVA={r['legal_validity_accuracy']}, ICR={r['invalid_citation_rate']})"
        )

    print("\nDone.")


if __name__ == "__main__":
    main()
