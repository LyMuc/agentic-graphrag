"""Tham số thời gian khi chạy Cypher retriever."""
from __future__ import annotations

from datetime import date
from typing import Any


def today_str() -> str:
    return date.today().strftime("%Y-%m-%d")


def attach_runtime_dates(runtime_params: dict[str, Any], target_date: str) -> dict[str, Any]:
    """Gắn target_date (mốc sự kiện) và query_date (ngày đặt câu hỏi = today)."""
    runtime_params["target_date"] = target_date
    runtime_params["query_date"] = today_str()
    return runtime_params
