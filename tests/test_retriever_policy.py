from __future__ import annotations

from retriever_policy import PolicyCandidate, evaluate_retriever_policy


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


def test_fallback_keeps_single_known_candidate_when_phrase_misses():
    decision = evaluate_retriever_policy(
        "Tình huống này của tôi nên giải quyết thế nào?",
        [PolicyCandidate("cap_duong", confidence_score=0.72)],
    )
    assert decision.final_tools == ["cap_duong"]
    assert decision.fallback_tool == "cap_duong"
    assert decision.rejected_tools == {}
    assert decision.candidate_confidences == {"cap_duong": 0.72}


def test_fallback_prefers_highest_confidence_known_candidate():
    decision = evaluate_retriever_policy(
        "Tình huống này của tôi nên giải quyết thế nào?",
        [
            PolicyCandidate("che_do_tai_san_cua_vo_chong", confidence_score=0.25),
            PolicyCandidate("cap_duong", confidence_score=0.91),
        ],
    )
    assert decision.final_tools == ["cap_duong"]
    assert decision.fallback_tool == "cap_duong"
    assert "che_do_tai_san_cua_vo_chong" in decision.rejected_tools


def test_fallback_uses_router_order_when_confidence_missing():
    decision = evaluate_retriever_policy(
        "Tình huống này của tôi nên giải quyết thế nào?",
        ["che_do_tai_san_cua_vo_chong", "cap_duong"],
    )
    assert decision.final_tools == ["che_do_tai_san_cua_vo_chong"]
    assert decision.fallback_tool == "che_do_tai_san_cua_vo_chong"
    assert "cap_duong" in decision.rejected_tools


def test_no_fallback_when_at_least_one_retriever_matches_trigger():
    decision = evaluate_retriever_policy(
        DIVORCE_PROPERTY_QUESTION,
        [
            PolicyCandidate("chia_tai_san_sau_ly_hon", confidence_score=0.40),
            PolicyCandidate("dai_dien_trach_nhiem_vo_chong", confidence_score=0.99),
        ],
    )
    assert decision.fallback_tool is None
    assert "chia_tai_san_sau_ly_hon" in decision.final_tools
    assert "dai_dien_trach_nhiem_vo_chong" in decision.rejected_tools


def test_unknown_retriever_is_not_fallback_candidate():
    decision = evaluate_retriever_policy(
        "Tình huống này của tôi nên giải quyết thế nào?",
        [PolicyCandidate("unknown_tool_xyz", confidence_score=1.0)],
    )
    assert decision.final_tools == []
    assert decision.fallback_tool is None
    assert decision.rejected_tools == {"unknown_tool_xyz": "Unknown retriever name."}


if __name__ == "__main__":
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    for fn in (
        test_keeps_router_candidate_names,
        test_rejects_dai_dien_false_positive_vay_particle,
        test_keeps_dai_dien_when_debt_phrase_present,
        test_filter_only_never_adds_tools,
        test_fallback_keeps_single_known_candidate_when_phrase_misses,
        test_fallback_prefers_highest_confidence_known_candidate,
        test_fallback_uses_router_order_when_confidence_missing,
        test_no_fallback_when_at_least_one_retriever_matches_trigger,
        test_unknown_retriever_is_not_fallback_candidate,
    ):
        fn()
        print("ok", fn.__name__)
