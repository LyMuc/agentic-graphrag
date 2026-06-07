"""Tests for router benchmark metrics (topic_label matching)."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BENCHMARK_DIR = REPO_ROOT / "benchmark_dataset"
for path in (str(REPO_ROOT), str(BENCHMARK_DIR)):
    if path not in sys.path:
        sys.path.insert(0, path)

from scripts._router_metrics import compute_metrics, topic_set  # noqa: E402


def test_exact_retriever_match():
    metrics = compute_metrics(
        ["chia_tai_san_sau_ly_hon"],
        expected_retrievers=["chia_tai_san_sau_ly_hon"],
    )
    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 1.0
    assert metrics["f1"] == 1.0
    assert metrics["error_types"] == ["Đúng"]
    assert metrics["passed"] is True


def test_multiple_expected_retrievers():
    metrics = compute_metrics(
        ["che_do_tai_san_cua_vo_chong", "chia_tai_san_sau_ly_hon"],
        expected_retrievers=[
            "che_do_tai_san_cua_vo_chong",
            "chia_tai_san_sau_ly_hon",
        ],
    )
    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 1.0
    assert metrics["missing"] == []
    assert metrics["extra"] == []


def test_extra_retriever():
    metrics = compute_metrics(
        ["chia_tai_san_sau_ly_hon", "quy_dinh_chung_ly_hon"],
        expected_retrievers=["chia_tai_san_sau_ly_hon"],
    )
    assert metrics["precision"] == 0.5
    assert metrics["recall"] == 1.0
    assert "Thừa" in metrics["error_types"]
    assert metrics["passed"] is False


def test_missing_retriever():
    metrics = compute_metrics(
        ["quy_dinh_chung_ly_hon"],
        expected_retrievers=["chia_tai_san_sau_ly_hon"],
    )
    assert metrics["recall"] == 0.0
    assert "Thiếu" in metrics["error_types"]


def test_legacy_alias_nghia_vu_cap_duong():
    keys = topic_set(["nghia_vu_cap_duong"])
    assert "cap_duong" in keys


def test_unknown_tool_name_exact_match_only():
    metrics = compute_metrics(
        ["unknown_tool_xyz"],
        expected_retrievers=["unknown_tool_xyz"],
    )
    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 1.0

    metrics2 = compute_metrics(
        ["unknown_tool_xyz"],
        expected_retrievers=["other_unknown"],
    )
    assert metrics2["precision"] == 0.0
    assert metrics2["recall"] == 0.0
