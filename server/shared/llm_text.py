"""Tiện ích làm sạch văn bản trả về từ LLM (gỡ code fence).

Tách từ ``utils/utils.py`` trong Phase 1 refactor.
"""
from __future__ import annotations

import re


def strip_code_fences(text: str) -> str:
    text = text.strip()
    # remove ```json or ``` and closing ```
    text = re.sub(r"^```json\s*|^```\s*|```$", "", text, flags=re.IGNORECASE).strip()
    return text


def strip_code_cypher(text: str) -> str:
    text = text.strip()
    # remove ```json or ``` and closing ```
    text = re.sub(r"^```(?:\w+)?\s*|```$", "", text, flags=re.IGNORECASE).strip()
    return text
