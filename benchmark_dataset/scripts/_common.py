"""
Common constants and helpers shared by every benchmark/test script.

Schema-as-source-of-truth: change column names HERE, not in individual scripts.
"""

from __future__ import annotations

import json
import os
import shutil
import time
import hashlib
from datetime import datetime
from typing import Any, Iterable

import pandas as pd

PACKAGE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BENCHMARK_DIR = os.path.join(PACKAGE_DIR, "benchmark")
BENCHMARK_GROUPED_DIR = os.path.join(PACKAGE_DIR, "benchmark_grouped")
TEST_VERSIONS_DIR = os.path.join(PACKAGE_DIR, "test_versions")
TEST_FINAL_DIR = os.path.join(PACKAGE_DIR, "test_final")
STATE_DIR = os.path.join(PACKAGE_DIR, "_state")
BACKUPS_DIR = os.path.join(STATE_DIR, "backups")
MANIFEST_PATH = os.path.join(STATE_DIR, "mapped_manifest.json")

# 11 canonical "hard benchmark" columns, in display order.
BENCHMARK_COLUMNS: list[str] = [
    "question",
    "ground_truth",
    "chu_de_phap_ly",
    "loai_cau_hoi",
    "van_ban_phap_luat_lien_quan",
    "tinh_trang_hieu_luc",
    "can_cu_phap_ly_chinh",
    "can_cu_phap_ly_bo_tro",
    "van_ban_huong_dan_sua_doi_bo_sung_thay_the",
    "can_cu_khong_nen_ap_dung",
    "quan_he_chong_cheo_mau_thuan",
]

# Columns whose natural representation is a JSON list or dict (NOT a string).
# JSON files keep these as native arrays/objects; CSV files store them as
# JSON-encoded strings (because CSV can't hold nested data) and we parse
# them back on read.
NESTED_COLUMNS: dict[str, type] = {
    "van_ban_phap_luat_lien_quan": list,
    "tinh_trang_hieu_luc": dict,
    "can_cu_phap_ly_chinh": list,
    "can_cu_phap_ly_bo_tro": list,
    "van_ban_huong_dan_sua_doi_bo_sung_thay_the": list,
    "can_cu_khong_nen_ap_dung": list,
    "quan_he_chong_cheo_mau_thuan": list,
}

# Core columns the user must fill before a row is considered "ready to be
# mapped" into a test version. ALL of these must be non-empty (non-empty
# string for scalars, non-empty list/dict for nested).
#
# The OPTIONAL_FILL_COLUMNS below are NOT required: it is perfectly valid
# for them to remain [] meaning "no relevant item exists". A row with all
# 4 core columns filled is mapped regardless of optional column state.
REQUIRED_FILL_COLUMNS: list[str] = [
    "loai_cau_hoi",                  # scalar: e.g. "Lý thuyết", "Tình huống"
    "van_ban_phap_luat_lien_quan",   # list: at least 1 referenced law
    "tinh_trang_hieu_luc",           # dict: status for at least 1 article
    "can_cu_phap_ly_chinh",          # list: at least 1 primary legal basis
]

OPTIONAL_FILL_COLUMNS: list[str] = [
    "can_cu_phap_ly_bo_tro",
    "van_ban_huong_dan_sua_doi_bo_sung_thay_the",
    "can_cu_khong_nen_ap_dung",
    "quan_he_chong_cheo_mau_thuan",
]

# Evaluation columns added (empty) to every test-version row. Position of
# `chatbot_answer` (right after `ground_truth`) is enforced via TEST_COLUMNS.
EVAL_COLUMNS_TAIL: list[str] = [
    "legal_citation_accuracy",
    "so_can_cu_con_hieu_luc",
    "tong_so_can_cu_duoc_neu_ra",
    "context",
    "citation_prioritization_accuracy",
    "co_loi_hieu_luc",
    "hallucination_rate",
    "faithfulness",
    "context_recall",
    "answer_correctness",
]

# Full test-version schema (22 columns) in display order.
TEST_COLUMNS: list[str] = (
    ["question", "ground_truth", "chatbot_answer"]
    + [c for c in BENCHMARK_COLUMNS if c not in ("question", "ground_truth")]
    + EVAL_COLUMNS_TAIL
)


def is_filled(value: Any) -> bool:
    """A cell counts as 'filled' iff it carries meaningful content:
      - lists/dicts/tuples/sets: have at least one item
      - strings: non-empty after strip, and not the literal 'nan'
      - everything else (numbers, etc.): truthy and not NaN
    """
    if value is None:
        return False
    if isinstance(value, (list, dict, tuple, set)):
        return len(value) > 0
    if isinstance(value, float):
        try:
            if pd.isna(value):
                return False
        except Exception:
            pass
    s = str(value).strip()
    if s == "" or s.lower() == "nan":
        return False
    return True


def empty_for(col: str) -> Any:
    """Return the canonical empty placeholder for a given column:
    [] for list-typed nested cols, {} for dict-typed, '' for scalars."""
    if col in NESTED_COLUMNS:
        return NESTED_COLUMNS[col]()
    return ""


def question_id(question: str) -> str:
    """Stable 12-char id for a question (independent of row order)."""
    normalized = " ".join(str(question).strip().split())
    return hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:12]


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def read_json(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        return [data]
    return data


def write_json(path: str, records: list[dict]) -> None:
    ensure_dir(os.path.dirname(path))
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def _csv_encode_nested(value: Any) -> str:
    """Encode a nested cell (list/dict) as a compact JSON string for CSV."""
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    if value is None:
        return ""
    return str(value)


def write_csv(path: str, df: pd.DataFrame) -> None:
    """Write a DataFrame to CSV, encoding nested cells as JSON strings so
    they survive the round-trip through CSV's flat format."""
    ensure_dir(os.path.dirname(path))
    df_for_csv = df.copy()
    for col in df_for_csv.columns:
        if col in NESTED_COLUMNS:
            df_for_csv[col] = df_for_csv[col].map(_csv_encode_nested)
    tmp = path + ".tmp"
    df_for_csv.to_csv(tmp, index=False, encoding="utf-8-sig")
    os.replace(tmp, path)


def _coerce_scalar(value: Any) -> str:
    """Coerce a value for a SCALAR column into a plain string.

    NaN/None become "". list/dict (which shouldn't appear in scalar cols,
    but might if user mis-typed) become their JSON representation so the
    DataFrame stays hashable for groupby.
    """
    if value is None:
        return ""
    if isinstance(value, float):
        try:
            if pd.isna(value):
                return ""
        except Exception:
            pass
    if isinstance(value, (list, dict, tuple, set)):
        try:
            return json.dumps(value, ensure_ascii=False)
        except Exception:
            return str(value)
    return str(value)


def _coerce_nested(value: Any, kind: type) -> Any:
    """Coerce a value for a NESTED column into its native list/dict form.

    Accepts:
      - native list/dict (returned as-is, must match `kind`)
      - JSON string (parsed back to native)
      - None / NaN / "" / "nan" (returned as empty kind())
      - tuple/set when expected list (converted)
    Anything else falls back to an empty kind() instance.
    """
    if value is None:
        return kind()
    if isinstance(value, kind):
        return value
    if isinstance(value, float):
        try:
            if pd.isna(value):
                return kind()
        except Exception:
            pass
    if isinstance(value, str):
        s = value.strip()
        if s == "" or s.lower() == "nan":
            return kind()
        try:
            parsed = json.loads(s)
            if isinstance(parsed, kind):
                return parsed
        except Exception:
            pass
        return kind()
    if kind is list and isinstance(value, (tuple, set)):
        return list(value)
    return kind()


def normalize_columns(df: pd.DataFrame, schema: Iterable[str]) -> pd.DataFrame:
    """Return df with EXACTLY `schema` columns, in that order.

    - Missing columns are added with `empty_for(col)` (list/dict/string).
    - Extra columns are dropped.
    - Scalar columns are coerced to plain strings.
    - Nested columns (NESTED_COLUMNS) are coerced to their native type
      (list or dict); JSON strings get parsed back to native.
    """
    schema = list(schema)
    for col in schema:
        if col not in df.columns:
            df[col] = [empty_for(col)] * len(df)
    df = df[schema].copy()
    for col in schema:
        if col in NESTED_COLUMNS:
            kind = NESTED_COLUMNS[col]
            df[col] = df[col].map(lambda v, k=kind: _coerce_nested(v, k))
        else:
            df[col] = df[col].map(_coerce_scalar)
    return df


def list_benchmark_files() -> list[str]:
    """All non-helper qa_*.json files in benchmark/."""
    out: list[str] = []
    for name in sorted(os.listdir(BENCHMARK_DIR)):
        if not name.endswith(".json"):
            continue
        if name.startswith("_"):
            continue
        out.append(os.path.join(BENCHMARK_DIR, name))
    return out


def timestamp_tag() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def backup_paths(paths: Iterable[str], reason: str) -> str | None:
    """Copy each existing file in `paths` into _state/backups/<ts>_<reason>/
    preserving relative path from PACKAGE_DIR. Returns the backup folder or
    None if nothing was backed up."""
    paths = [p for p in paths if os.path.exists(p)]
    if not paths:
        return None
    ensure_dir(BACKUPS_DIR)
    folder = os.path.join(BACKUPS_DIR, f"{timestamp_tag()}_{reason}")
    ensure_dir(folder)
    for p in paths:
        rel = os.path.relpath(p, PACKAGE_DIR)
        dst = os.path.join(folder, rel)
        ensure_dir(os.path.dirname(dst))
        shutil.copy2(p, dst)
    return folder
