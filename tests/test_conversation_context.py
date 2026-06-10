from __future__ import annotations

from application.conversation_context import (
    build_turn_anchor,
    build_working_history,
    create_retrieval_memory_entries,
    restore_conversation_state,
    validate_reuse_request,
)
from application.legal_context import (
    build_legal_context_bundle,
    encode_legal_context_bundle,
)


def _encoded_context(
    *,
    target_date: str = "2026-06-11",
    is_user_provided_date: bool = False,
) -> str:
    """Create one encoded legal bundle for conversation-memory tests.

    Args:
        target_date: Applicable date stored in the bundle.
        is_user_provided_date: Whether the date was explicitly supplied.

    Returns:
        Encoded LegalContextBundle string.
    """

    context_tho = {
        "can_cu_chinh": [
            {
                "id_goc_tu_router": "Luat_HNGD_2014_Dieu_8",
                "id_thuc_te_ap_dung": "Luat_HNGD_2014_Dieu_8",
                "noidung": "Điều kiện kết hôn",
                "cap_bac": 1,
                "het_hieu_luc": False,
                "ngay_hieu_luc": "2015-01-01",
                "ngay_het_hieu_luc": None,
                "id_sua_doi": None,
            }
        ],
        "can_cu_huong_dan": [],
        "can_cu_bo_tro": [],
        "lien_ket_huong_dan": [],
        "can_cu_sap_hieu_luc": [],
        "lien_ket_sap_hieu_luc": [],
        "can_cu_mau_thuan": [],
        "quy_dinh_hien_hanh_doi_chieu": [],
    }
    return encode_legal_context_bundle(
        build_legal_context_bundle(
            context_tho,
            target_date,
            is_user_provided_date,
            retriever_name="dieu_kien_ket_hon",
            template_name="dieu_kien",
            citation_links={},
        )
    )


def _memory_entry(
    *,
    ref: str = "ctx-1",
    thread_id: str = "thread-1",
    kg_version: str = "kg-1",
    target_date: str = "2026-06-11",
    explicit: bool = False,
) -> dict:
    """Create one retrieval-memory fixture.

    Args:
        ref: Context reference identifier.
        thread_id: Owning thread identifier.
        kg_version: Knowledge-graph version.
        target_date: Date stored in the encoded bundle.
        explicit: Whether the bundle date came from the user.

    Returns:
        Retrieval-memory entry dictionary.
    """

    return {
        "context_ref": ref,
        "turn_id": "turn-1",
        "thread_id": thread_id,
        "retriever_name": "dieu_kien_ket_hon",
        "resolved_query": "Nam 18 tuổi có được kết hôn không?",
        "encoded_contexts": [
            _encoded_context(
                target_date=target_date,
                is_user_provided_date=explicit,
            )
        ],
        "target_dates": [target_date],
        "kg_version": kg_version,
        "created_at": "2026-06-11T00:00:00+00:00",
    }


def test_working_history_keeps_recent_turns_and_relevant_old_anchor():
    """Verify bounded history combines recent full turns with an old anchor."""

    history = []
    anchors = []
    for index in range(1, 7):
        history.extend(
            [
                {"role": "user", "content": f"Câu hỏi lượt {index}"},
                {"role": "assistant", "content": f"Câu trả lời lượt {index}"},
            ]
        )
        anchors.append(
            {
                "turn_id": f"turn-{index}",
                "resolved_queries": [
                    "Căn nhà mua trước hôn nhân" if index == 1 else f"Vấn đề {index}"
                ],
                "retriever_names": ["che_do_tai_san_cua_vo_chong"],
                "context_refs": [f"ctx-{index}"],
            }
        )

    working = build_working_history(
        history,
        anchors,
        current_query="Nếu bán căn nhà thì sao?",
        recent_full_turns=2,
        max_tokens=500,
        older_turn_index_limit=10,
    )

    assert working[0]["role"] == "system"
    assert "turn-1" in working[0]["content"]
    assert any(message["content"] == "Câu hỏi lượt 5" for message in working)
    assert any(message["content"] == "Câu hỏi lượt 6" for message in working)
    assert not any(message["content"] == "Câu hỏi lượt 2" for message in working)


def test_reuse_validation_accepts_matching_current_context():
    """Verify structurally matching current-law cache entries are accepted."""

    entry = _memory_entry()
    validation = validate_reuse_request(
        tool_name="dieu_kien_ket_hon",
        tool_args={
            "context_action": "reuse",
            "context_refs": ["ctx-1"],
            "time_scope": "current",
        },
        memory={"ctx-1": entry},
        thread_id="thread-1",
        kg_version="kg-1",
        today="2026-06-11",
    )

    assert validation.allowed is True
    assert len(validation.contexts) == 1


def test_reuse_validation_rejects_date_kg_and_thread_mismatches():
    """Verify date, KG version, and thread mismatches each invalidate reuse."""

    entry = _memory_entry()
    base_args = {
        "context_action": "reuse",
        "context_refs": ["ctx-1"],
        "time_scope": "current",
    }

    stale_kg = validate_reuse_request(
        tool_name="dieu_kien_ket_hon",
        tool_args=base_args,
        memory={"ctx-1": entry},
        thread_id="thread-1",
        kg_version="kg-2",
        today="2026-06-11",
    )
    wrong_thread = validate_reuse_request(
        tool_name="dieu_kien_ket_hon",
        tool_args=base_args,
        memory={"ctx-1": entry},
        thread_id="thread-2",
        kg_version="kg-1",
        today="2026-06-11",
    )
    wrong_date = validate_reuse_request(
        tool_name="dieu_kien_ket_hon",
        tool_args={
            **base_args,
            "time_scope": "explicit",
            "target_date": "2020",
        },
        memory={"ctx-1": entry},
        thread_id="thread-1",
        kg_version="kg-1",
        today="2026-06-11",
    )

    assert stale_kg.allowed is False
    assert wrong_thread.allowed is False
    assert wrong_date.allowed is False


def test_memory_entry_anchor_and_resume_round_trip():
    """Verify persisted memory and anchors can be restored with chat messages."""

    tool_response = [
        {
            "retriever_name": "dieu_kien_ket_hon",
            "resolved_query": "Nữ 18 tuổi có được kết hôn không?",
            "contexts": [_encoded_context()],
            "cache_status": "retrieved",
        }
    ]
    entries = create_retrieval_memory_entries(
        tool_response,
        turn_id="turn-2",
        thread_id="thread-1",
        kg_version="kg-1",
    )
    anchor = build_turn_anchor(
        turn_id="turn-2",
        tool_response=tool_response,
        new_memory_entries=entries,
    )
    steps = [
        {"type": "user_message", "output": "Còn nữ thì sao?"},
        {"type": "assistant_message", "output": "Nữ phải từ đủ 18 tuổi."},
        {
            "type": "tool",
            "metadata": {
                "retrieval_memory_entries": entries,
                "turn_anchor": anchor,
            },
        },
    ]

    history, memory, anchors = restore_conversation_state(steps)

    assert len(entries) == 1
    assert anchor is not None
    assert entries[0]["context_ref"] in anchor["context_refs"]
    assert len(history) == 2
    assert entries[0]["context_ref"] in memory
    assert anchors == [anchor]
