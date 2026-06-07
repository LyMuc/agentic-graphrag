from __future__ import annotations

import re
import unicodedata
from typing import Literal

from rapidfuzz import fuzz

MatchMode = Literal["exact", "folded", "fuzzy"]

DEFAULT_FUZZY_THRESHOLD = 0.88


def prepare_question(text: str) -> str:
    """Chuẩn hóa câu hỏi để so khớp phrase: lowercase, giữ dấu tiếng Việt.

    Args:
        text: Câu hỏi thô từ người dùng hoặc benchmark.

    Returns:
        Chuỗi đã lowercase, khoảng trắng gọn, vẫn giữ dấu và chữ đ.
    """
    text = str(text or "").lower()
    text = re.sub(r"[^\w]+", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()


def fold_vi(text: str) -> str:
    """Bỏ dấu tiếng Việt chỉ dùng khi so sánh phrase (không lưu câu hỏi).

    Args:
        text: Chuỗi đã prepare hoặc phrase cần fold.

    Returns:
        Chuỗi không dấu, chữ thường.
    """
    text = str(text or "").lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return text.replace("đ", "d").replace("Đ", "d")


def _phrase_word_count(phrase: str) -> int:
    """Đếm số từ trong phrase để xác định cửa sổ fuzzy.

    Args:
        phrase: Cụm từ đã prepare.

    Returns:
        Số từ (tối thiểu 1).
    """
    words = prepare_question(phrase).split()
    return max(1, len(words))


def match_phrase(
    phrase: str,
    prepared_question: str,
    *,
    folded_question: str | None = None,
    fuzzy_threshold: float = DEFAULT_FUZZY_THRESHOLD,
) -> tuple[bool, MatchMode | None]:
    """Kiểm tra một phrase có xuất hiện trong câu hỏi không.

    Thứ tự: exact substring -> folded substring -> fuzzy sliding window.

    Args:
        phrase: Cụm từ trigger (có dấu).
        prepared_question: Câu hỏi đã qua prepare_question.
        folded_question: Bản fold của câu hỏi (tùy chọn, tính nếu None).
        fuzzy_threshold: Ngưỡng ratio fuzzy (0-100 scale qua rapidfuzz).

    Returns:
        (matched, mode) — mode là exact/folded/fuzzy hoặc None nếu không khớp.
    """
    prepared_phrase = prepare_question(phrase)
    if not prepared_phrase or not prepared_question:
        return False, None

    if prepared_phrase in prepared_question:
        return True, "exact"

    folded_q = folded_question if folded_question is not None else fold_vi(prepared_question)
    folded_p = fold_vi(prepared_phrase)
    if folded_p in folded_q:
        return True, "folded"

    q_words = prepared_question.split()
    p_words = prepared_phrase.split()
    window = len(p_words)
    if window > len(q_words):
        return False, None

    threshold = fuzzy_threshold * 100
    for start in range(len(q_words) - window + 1):
        window_text = " ".join(q_words[start : start + window])
        ratio = fuzz.ratio(fold_vi(window_text), folded_p)
        if ratio >= threshold:
            return True, "fuzzy"

    return False, None


def match_phrase_group(
    phrases: tuple[str, ...],
    prepared_question: str,
    *,
    folded_question: str | None = None,
    fuzzy_threshold: float = DEFAULT_FUZZY_THRESHOLD,
) -> tuple[bool, str | None, MatchMode | None]:
    """OR trong một group: khớp nếu >= 1 phrase khớp.

    Args:
        phrases: Các cụm từ thay thế nhau (OR).
        prepared_question: Câu hỏi đã prepare.
        folded_question: Bản fold câu hỏi (cache).
        fuzzy_threshold: Ngưỡng fuzzy.

    Returns:
        (matched, matched_phrase, mode).
    """
    folded_q = folded_question if folded_question is not None else fold_vi(prepared_question)
    for phrase in phrases:
        matched, mode = match_phrase(
            phrase,
            prepared_question,
            folded_question=folded_q,
            fuzzy_threshold=fuzzy_threshold,
        )
        if matched:
            return True, phrase, mode
    return False, None, None


def match_phrase_groups(
    groups: tuple[tuple[str, ...], ...],
    prepared_question: str,
    *,
    fuzzy_threshold: float = DEFAULT_FUZZY_THRESHOLD,
) -> bool:
    """AND giữa các group: mỗi group phải có >= 1 phrase khớp.

    Args:
        groups: Tuple các phrase group; mỗi group là OR.
        prepared_question: Câu hỏi đã prepare.
        fuzzy_threshold: Ngưỡng fuzzy.

    Returns:
        True nếu mọi group đều khớp.
    """
    if not groups:
        return False
    folded_q = fold_vi(prepared_question)
    for group in groups:
        matched, _, _ = match_phrase_group(
            group,
            prepared_question,
            folded_question=folded_q,
            fuzzy_threshold=fuzzy_threshold,
        )
        if not matched:
            return False
    return True
