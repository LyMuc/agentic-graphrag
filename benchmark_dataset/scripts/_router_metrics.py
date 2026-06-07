"""Shared precision/recall/f1 metrics for router agent benchmark."""

from __future__ import annotations

from typing import Any

from application.retriever_catalog import retriever_topic_key


def topic_set(values: list[str] | None) -> set[str]:
    """Chuẩn hóa tên retriever về topic_label để so metrics.

    Args:
        values: Danh sách tên tool retriever.

    Returns:
        Set topic_label tương ứng.
    """
    return {retriever_topic_key(value) for value in (values or []) if value}


def _safe_div(num: int, den: int, default: float) -> float:
    if den == 0:
        return default
    return num / den


def compute_metrics(
    actual: list[str],
    *,
    expected_retrievers: list[str] | None = None,
) -> dict[str, Any]:
    """So sánh actual vs expected theo topic_label.

    Args:
        actual: Retriever thực tế (llm_candidates hoặc policy output).
        expected_retrievers: Ground truth.

    Returns:
        precision, recall, f1, error_types, missing, extra, topic keys.
    """
    actual_set = topic_set(actual)
    expected = topic_set(expected_retrievers)

    hits = actual_set & expected
    missing = expected - actual_set
    extra = actual_set - expected

    precision = _safe_div(len(hits), len(actual_set), 1.0 if not expected else 0.0)
    recall = _safe_div(len(hits), len(expected), 1.0 if not actual_set else 0.0)
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    error_types: list[str] = []
    if missing:
        error_types.append("Thiếu")
    if extra:
        error_types.append("Thừa")
    if not error_types:
        error_types = ["Đúng"]

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "error_types": error_types,
        "missing": sorted(missing),
        "extra": sorted(extra),
        "actual_topic_keys": sorted(actual_set),
        "expected_topic_keys": sorted(expected),
        "passed": error_types == ["Đúng"],
    }
