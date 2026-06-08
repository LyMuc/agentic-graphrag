"""Ánh xạ thuật ngữ thông thường → param chuẩn cho topic cap_duong."""
from __future__ import annotations

import re
from typing import Any, Optional

COMMON_TO_LEGAL_TERMS: dict[str, dict[str, Any]] = {
    "quan_he": {
        "cha cấp dưỡng con": "cha_me_cho_con",
        "mẹ cấp dưỡng con": "cha_me_cho_con",
        "bố nuôi con": "cha_me_cho_con",
        "người không trực tiếp nuôi con": "cha_me_khong_truc_tiep_nuoi_con_sau_ly_hon",
        "bố/mẹ không nuôi con": "cha_me_khong_truc_tiep_nuoi_con_sau_ly_hon",
        "con cấp dưỡng cha mẹ": "con_cho_cha_me",
        "nuôi cha mẹ già": "con_cho_cha_me",
        "anh chị em nuôi nhau": "anh_chi_em_voi_nhau",
        "ông bà cấp dưỡng cháu": "ong_ba_cho_chau",
        "ông bà nuôi cháu thay": "ong_ba_cho_chau",
        "cháu cấp dưỡng ông bà": "chau_cho_ong_ba",
        "cô dì chú cậu bác cấp dưỡng cháu": "co_di_chu_cau_bac_cho_chau_ruot",
        "cháu cấp dưỡng cô dì chú cậu bác": "chau_ruot_cho_co_di_chu_cau_bac",
        "vợ cũ": "vo_chong_sau_ly_hon",
        "chồng cũ": "vo_chong_sau_ly_hon",
        "cấp dưỡng sau ly hôn": "vo_chong_sau_ly_hon",
    },
    "boi_canh": {
        "con ngoài giá thú": "con_ngoai_gia_thu",
        "con ngoài hôn nhân": "con_ngoai_gia_thu",
        "không đăng ký kết hôn": "khong_dang_ky_ket_hon",
        "không có giấy kết hôn": "khong_dang_ky_ket_hon",
        "sau ly hôn": "sau_ly_hon",
        "không ở cùng con": "khong_song_chung",
        "sống chung nhưng bỏ mặc": "song_chung_vi_pham_nuoi_duong",
        "sống chung nhưng không nuôi": "song_chung_vi_pham_nuoi_duong",
    },
    "tinh_trang_nguoi_duoc_cap_duong": {
        "chưa đủ 18 tuổi": "chua_thanh_nien",
        "trẻ em": "chua_thanh_nien",
        "con nhỏ": "chua_thanh_nien",
        "không có khả năng lao động và không có tài sản": "thanh_nien_khong_kha_nang_lao_dong_khong_tai_san",
        "đau yếu": "kho_khan_tung_thieu",
        "không việc làm": "kho_khan_tung_thieu",
        "túng thiếu": "kho_khan_tung_thieu",
        "không còn ai nuôi": "khong_co_nguoi_khac_cap_duong",
        "cha mẹ không thể cấp dưỡng": "khong_co_nguoi_khac_cap_duong",
    },
    "khia_canh": {
        "đến bao nhiêu tuổi": "thoi_han_theo_tinh_trang",
        "cấp dưỡng đến khi nào": "thoi_han_theo_tinh_trang",
        "tài sản riêng để cấp dưỡng": "nguon_tai_san_thuc_hien",
        "đổi cách trả": "thay_doi_phuong_thuc",
        "đổi kỳ trả": "thay_doi_phuong_thuc",
        "tạm dừng": "tam_ngung_do_kho_khan",
        "tạm ngừng cấp dưỡng": "tam_ngung_do_kho_khan",
        "ai có quyền yêu cầu": "chu_the_co_quyen_yeu_cau",
        "người nào được kiện": "chu_the_co_quyen_yeu_cau",
        "trốn tránh": "tron_tranh",
        "không chịu cấp dưỡng": "tron_tranh",
        "không muốn nhận cấp dưỡng": "khong_yeu_cau_nhan_cap_duong",
        "không yêu cầu cấp dưỡng": "khong_yeu_cau_nhan_cap_duong",
        "đổi người nuôi con": "thay_doi_nguoi_truc_tiep_nuoi",
        "thay đổi người trực tiếp nuôi": "thay_doi_nguoi_truc_tiep_nuoi",
    },
    "khia_canh_muc": {
        "mức bao nhiêu": "xac_dinh_muc",
        "tiền cấp dưỡng bao nhiêu": "xac_dinh_muc",
        "tối thiểu": "muc_toi_thieu",
        "ít nhất": "muc_toi_thieu",
        "mức sàn": "muc_toi_thieu",
        "tăng mức": "thay_doi_muc",
        "giảm mức": "thay_doi_muc",
        "đổi mức": "thay_doi_muc",
        "một người cấp dưỡng nhiều người": "mot_nguoi_nhieu_nguoi",
        "nhiều người cùng cấp dưỡng": "nhieu_nguoi_cung_cap_duong",
        "cùng góp tiền": "nhieu_nguoi_cung_cap_duong",
    },
    "chu_ky": {
        "hàng tháng": "hang_thang",
        "mỗi tháng": "hang_thang",
        "hàng quý": "hang_quy",
        "mỗi quý": "hang_quy",
        "nửa năm": "nua_nam",
        "sáu tháng một lần": "nua_nam",
        "hàng năm": "hang_nam",
        "mỗi năm": "hang_nam",
        "cấp dưỡng một lần": "mot_lan",
        "trả một cục": "mot_lan",
    },
    "kho_khan_kinh_te": {
        "nợ ngân hàng": "co",
        "mất việc": "co",
        "bệnh": "co",
        "ở nhờ": "co",
        "không có khả năng trả": "co",
    },
    "ly_do_cham_dut": {
        "đủ tuổi và tự đi làm": "nguoi_duoc_cap_duong_tu_nuoi_minh",
        "có tài sản tự nuôi": "nguoi_duoc_cap_duong_tu_nuoi_minh",
        "được nhận làm con nuôi": "duoc_nhan_lam_con_nuoi",
        "chuyển sang trực tiếp nuôi": "nguoi_cap_duong_truc_tiep_nuoi",
        "chết": "mot_ben_chet",
        "qua đời": "mot_ben_chet",
        "vợ cũ tái hôn": "ben_duoc_cap_duong_tai_hon",
        "chồng cũ tái hôn": "ben_duoc_cap_duong_tai_hon",
        "kết hôn lại": "ben_duoc_cap_duong_tai_hon",
        "chấm dứt": "tat_ca",
        "hết nghĩa vụ": "tat_ca",
    },
    "nguoi_yeu_cau": {
        "mẹ khởi kiện": "cha_me",
        "cha khởi kiện": "cha_me",
        "mẹ khởi kiện cho con": "cha_me",
        "người thân": "nguoi_than_thich",
        "ông bà": "nguoi_than_thich",
        "họ hàng yêu cầu": "nguoi_than_thich",
        "hội phụ nữ": "hoi_lien_hiep_phu_nu",
        "hội liên hiệp phụ nữ": "hoi_lien_hiep_phu_nu",
    },
    "tinh_trang_thuc_hien": {
        "không chịu cấp dưỡng": "khong_tu_nguyen",
        "không tự nguyện": "khong_tu_nguyen",
        "trốn tránh": "tron_tranh",
        "bỏ trốn để không cấp dưỡng": "tron_tranh",
        "chậm": "cham_thuc_hien",
        "phải đòi nhiều lần": "cham_thuc_hien",
    },
    "doi_tuong_nhan": {
        "nuôi con": "con",
        "con sau ly hôn": "con",
        "vợ cũ": "vo_chong_cu",
        "chồng cũ": "vo_chong_cu",
    },
    "doi_tuong_duoc_cap_duong": {
        "nuôi con": "con",
        "con sau ly hôn": "con",
        "vợ cũ": "vo_chong_cu",
        "chồng cũ": "vo_chong_cu",
    },
    "chu_ky_duoc_hoi": {
        "mỗi tháng": "hang_thang",
        "hằng tháng": "hang_thang",
    },
}


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().strip())


def resolve_term(field: str, raw_text: Optional[str]) -> Optional[Any]:
    if not raw_text or field not in COMMON_TO_LEGAL_TERMS:
        return None
    norm = _normalize(raw_text)
    mapping = COMMON_TO_LEGAL_TERMS[field]
    for pattern in sorted(mapping.keys(), key=len, reverse=True):
        if pattern.lower() in norm:
            return mapping[pattern]
    return None


def resolve_many(raw_text: Optional[str]) -> dict[str, Any]:
    """Quét toàn bộ field mapping — dùng khi cần gợi ý đa param từ cùng câu hỏi."""
    if not raw_text:
        return {}
    out: dict[str, Any] = {}
    for field in COMMON_TO_LEGAL_TERMS:
        val = resolve_term(field, raw_text)
        if val is not None:
            out[field] = val
    return out


__all__ = ["COMMON_TO_LEGAL_TERMS", "resolve_term", "resolve_many"]
