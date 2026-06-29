"""Tiện ích chung (đang refactor sang ``server/``).

Phase 1 đã chuyển renderer + codec helpers sang ``server.domain.legal``, datetime
helper sang ``server.shared.datetime_vn`` và strip-fence sang ``server.shared.llm_text``.
File này giữ lại các symbol chưa nằm trong phạm vi move (``TrichXuatLuat``,
``chuan_hoa_ket_qua_retriever``, ``extract_raw_ids_from_context``,
``lay_target_date_tu_extraction``) và re-export các symbol đã move để mọi import cũ
tiếp tục hoạt động.
"""
from __future__ import annotations

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional

# --- Re-export các symbol đã move (back-compat) ---
from server.shared.llm_text import strip_code_fences, strip_code_cypher
from server.shared.datetime_vn import chuan_hoa_thoi_diem_su_kien
from server.domain.legal.render import (
    chuan_hoa_Context_cho_LLM,
    _LOAI_TAC_DONG_LABEL,
    _LOAI_TAC_DONG_VAN_BAN_MOI,
    _DIEU_ID_RE,
    _dieu_level_id,
    _to_dieu_id,
    _format_date_vn,
    _extract_doc_name,
    _collect_dieu_ids_from_context,
    _collect_dieu_ids_for_bang_link,
    _fetch_tvpl_links,
    _fetch_provision_effective_dates,
)


def lay_target_date_tu_extraction(thoi_diem_su_kien, formatted_date: str):
    """Trả về (target_date, is_user_provide_date) sau khi chuẩn hóa mốc thời gian."""
    normalized = chuan_hoa_thoi_diem_su_kien(thoi_diem_su_kien)
    is_user_provide_date = bool(normalized)
    target_date = normalized or formatted_date
    return target_date, is_user_provide_date


class TrichXuatLuat(BaseModel):
    dieu_luat_ids: List[str] = Field(
        description="Danh sách ID điều luật cần dùng. (Có thể cần nhiều điều luật để trả lời đầy đủ câu hỏi)"
    )
    thoi_diem_su_kien: Optional[str] = Field(
        description=(
            "Năm/tháng/ngày xảy ra sự kiện trong câu hỏi. "
            "Định dạng 'YYYY-MM-DD'. Nếu người dùng chỉ nêu năm (vd: 2023), trả về 'YYYY' hoặc 'YYYY-01-01'. "
            "Nếu người dùng KHÔNG nhắc đến mốc thời gian, bắt buộc trả về null."
        ),
        default=None,
    )

    @field_validator("thoi_diem_su_kien", mode="before")
    @classmethod
    def _normalize_thoi_diem(cls, value):
        return chuan_hoa_thoi_diem_su_kien(value)


def _unique_non_empty(values):
    result = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result


def extract_raw_ids_from_context(context_tho):
    """Trích xuất các ID cần kiểm tra từ kết quả Cypher chưa chuẩn hóa."""
    can_cu_chinh = [
        item.get("id_thuc_te_ap_dung") or item.get("id")
        for item in context_tho.get("can_cu_chinh", [])
        if item
    ]
    can_cu_huong_dan = [
        item.get("id")
        for item in context_tho.get("can_cu_huong_dan", [])
        if item
    ]
    can_cu_bo_tro = [
        item.get("id")
        for item in context_tho.get("can_cu_bo_tro", [])
        if item
    ]
    can_cu_mau_thuan = [
        item.get("id_dich")
        for item in context_tho.get("can_cu_mau_thuan", [])
        if item
    ]
    can_cu_sap_hieu_luc = [
        item.get("id")
        for item in context_tho.get("can_cu_sap_hieu_luc", [])
        if item
    ]

    return {
        "can_cu_chinh": _unique_non_empty(can_cu_chinh),
        "can_cu_huong_dan": _unique_non_empty(can_cu_huong_dan),
        "can_cu_bo_tro": _unique_non_empty(can_cu_bo_tro),
        "can_cu_mau_thuan": _unique_non_empty(can_cu_mau_thuan),
        "can_cu_sap_hieu_luc": _unique_non_empty(can_cu_sap_hieu_luc),
    }


def chuan_hoa_ket_qua_retriever(records, target_date, is_user_provide_date):
    """Trả về đồng nhất raw_ids + contexts cho mọi retriever."""
    raw_ids = {
        "can_cu_chinh": [],
        "can_cu_huong_dan": [],
        "can_cu_bo_tro": [],
        "can_cu_mau_thuan": [],
        "can_cu_sap_hieu_luc": [],
    }
    contexts = []

    for record in records:
        context_tho = record["Context_Tho"]
        ids = extract_raw_ids_from_context(context_tho)
        for key, values in ids.items():
            raw_ids[key] = _unique_non_empty([*raw_ids[key], *values])

        contexts.append(chuan_hoa_Context_cho_LLM(record, target_date, is_user_provide_date))

    return {
        "raw_ids": raw_ids,
        "contexts": contexts,
    }
