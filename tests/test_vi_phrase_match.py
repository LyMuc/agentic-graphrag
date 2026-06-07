from __future__ import annotations

from application.vi_phrase_match import (
    match_phrase,
    match_phrase_group,
    prepare_question,
)


def test_prepare_question_keeps_diacritics():
    assert "ly hôn" in prepare_question("Định LY HÔN")


def test_exact_phrase_match():
    q = prepare_question("Chúng tôi định ly hôn")
    matched, mode = match_phrase("ly hôn", q)
    assert matched is True
    assert mode == "exact"


def test_folded_match_without_diacritics():
    q = prepare_question("dinh ly hon")
    matched, mode = match_phrase("ly hôn", q)
    assert matched is True
    assert mode == "folded"


def test_vay_is_not_vay_particle():
    q = prepare_question("định ly hôn. Vậy tôi có được chia tài sản không?")
    matched, _ = match_phrase("vay tiền", q)
    assert matched is False


def test_vay_tien_matches():
    q = prepare_question("chồng vay tiền ngân hàng")
    matched, mode = match_phrase("vay tiền", q)
    assert matched is True
    assert mode == "exact"


def test_phrase_group_or():
    q = prepare_question("tôi muốn chia tài sản")
    matched, phrase, _ = match_phrase_group(("nhà", "tài sản", "đất"), q)
    assert matched is True
    assert phrase == "tài sản"


if __name__ == "__main__":
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    for fn in (
        test_prepare_question_keeps_diacritics,
        test_exact_phrase_match,
        test_folded_match_without_diacritics,
        test_vay_is_not_vay_particle,
        test_vay_tien_matches,
        test_phrase_group_or,
    ):
        fn()
        print("ok", fn.__name__)
