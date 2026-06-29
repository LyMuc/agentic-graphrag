"""Chuẩn hoá mốc thời gian sự kiện tiếng Việt về ``YYYY-MM-DD``.

Tách từ ``utils/utils.py`` trong Phase 1 refactor (shared layer).
"""
from __future__ import annotations

import re
from datetime import date
from typing import Optional


def chuan_hoa_thoi_diem_su_kien(thoi_diem) -> Optional[str]:
    """
    Chuẩn hóa mốc thời gian sự kiện về YYYY-MM-DD.
    - Chỉ có năm (YYYY) -> YYYY-01-01
    - Chỉ có năm-tháng (YYYY-MM) -> YYYY-MM-01
    - Đã đủ ngày (YYYY-MM-DD) -> giữ nguyên
    """
    if thoi_diem is None:
        return None

    if isinstance(thoi_diem, date):
        return thoi_diem.strftime("%Y-%m-%d")

    s = str(thoi_diem).strip()
    if not s or s.lower() in ("null", "none"):
        return None

    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return s

    m = re.fullmatch(r"(\d{4})-(\d{1,2})", s)
    if m:
        year, month = m.groups()
        return f"{year}-{month.zfill(2)}-01"

    if re.fullmatch(r"\d{4}", s):
        return f"{s}-01-01"

    m = re.fullmatch(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", s)
    if m:
        day, month, year = m.groups()
        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"

    m = re.search(r"\b(19|20)\d{2}\b", s)
    if m:
        return f"{m.group()}-01-01"

    return s
