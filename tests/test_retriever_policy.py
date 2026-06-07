from __future__ import annotations

from application.retriever_policy import evaluate_retriever_policy


DIVORCE_PROPERTY_QUESTION = (
    "Xin cho hỏi: Tôi lấy chồng cách đây 05 năm, sinh được 1 bé trai 02 tuổi, "
    "tôi chỉ ở nhà nội trợ, còn mọi chi phí trong gia đình đều do chồng tôi đi làm mà có. "
    "Nhưng giờ đây chúng tôi sống không hạnh phúc và định ly hôn. "
    "Vậy tôi có được chia tài sản không?"
)

DEBT_QUESTION = (
    "Do có quá nhiều mâu thuẫn nên tôi và chồng quyết định đi đến ly hôn, "
    "chúng tôi đã thỏa thuận về nuôi con chung cũng như tài sản chung, "
    "Quyết định thuận tình ly hôn đã có, và nay tôi biết một vấn đề là trước đó "
    "(trong thời kỳ hôn nhân) do kinh doanh có vấn đề nên chồng tôi có vay số tiền "
    "để lớn, nay không có khả năng chi trả, tôi không rõ là mình đã ly hôn thì có "
    "phải cùng chịu trách nhiệm chi trả khoản vay đó không?"
)


def test_keeps_router_candidate_names():
    decision = evaluate_retriever_policy(
        DIVORCE_PROPERTY_QUESTION,
        ["chia_tai_san_sau_ly_hon", "che_do_tai_san_cua_vo_chong"],
    )
    assert "chia_tai_san_sau_ly_hon" in decision.final_tools
    assert "che_do_tai_san_cua_vo_chong" in decision.final_tools
    assert set(decision.final_tools).issubset(set(decision.llm_candidates))


def test_rejects_dai_dien_false_positive_vay_particle():
    decision = evaluate_retriever_policy(
        DIVORCE_PROPERTY_QUESTION,
        ["chia_tai_san_sau_ly_hon", "dai_dien_trach_nhiem_vo_chong"],
    )
    assert "dai_dien_trach_nhiem_vo_chong" in decision.rejected_tools
    assert "dai_dien_trach_nhiem_vo_chong" not in decision.final_tools


def test_keeps_dai_dien_when_debt_phrase_present():
    decision = evaluate_retriever_policy(
        DEBT_QUESTION,
        ["quy_dinh_chung_ly_hon", "dai_dien_trach_nhiem_vo_chong"],
    )
    assert "dai_dien_trach_nhiem_vo_chong" in decision.final_tools


def test_filter_only_never_adds_tools():
    decision = evaluate_retriever_policy(
        DIVORCE_PROPERTY_QUESTION,
        ["chia_tai_san_sau_ly_hon"],
    )
    assert decision.final_tools == ["chia_tai_san_sau_ly_hon"]
    assert len(decision.final_tools) <= len(decision.llm_candidates)


if __name__ == "__main__":
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    for fn in (
        test_keeps_router_candidate_names,
        test_rejects_dai_dien_false_positive_vay_particle,
        test_keeps_dai_dien_when_debt_phrase_present,
        test_filter_only_never_adds_tools,
    ):
        fn()
        print("ok", fn.__name__)
