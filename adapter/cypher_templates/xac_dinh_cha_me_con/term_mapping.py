"""Ánh xạ thuật ngữ thông thường → param chuẩn cho topic xac_dinh_cha_me_con."""
from __future__ import annotations

import re
from typing import Any, Optional

COMMON_TO_LEGAL_TERMS: dict[str, dict[str, Any]] = {
    "tinh_huong": {
        "sinh trong thời kỳ hôn nhân": "sinh_trong_thoi_ky_hon_nhan",
        "sinh khi đang là vợ chồng": "sinh_trong_thoi_ky_hon_nhan",
        "có thai trong thời kỳ hôn nhân": "co_thai_trong_thoi_ky_hon_nhan",
        "mang thai khi đang kết hôn": "co_thai_trong_thoi_ky_hon_nhan",
        "có thai trước khi kết hôn": "co_thai_truoc_ket_hon",
        "mang thai trước ngày cưới": "co_thai_truoc_ket_hon",
        "trong vòng 300 ngày": "sinh_trong_300_ngay_sau_cham_dut_hon_nhan",
        "4 tháng sau ly hôn": "sinh_trong_300_ngay_sau_cham_dut_hon_nhan",
        "8 tháng sau ly hôn": "sinh_trong_300_ngay_sau_cham_dut_hon_nhan",
        "trước ngày đăng ký kết hôn": "sinh_truoc_dang_ky_ket_hon_duoc_thua_nhan",
        "chưa đăng ký kết hôn nhưng cùng thừa nhận": "sinh_truoc_dang_ky_ket_hon_duoc_thua_nhan",
        "không thừa nhận con": "khong_thua_nhan_con",
        "phủ nhận con": "khong_thua_nhan_con",
        "không nhận là con": "khong_thua_nhan_con",
        "ivf": "vo_chong_ho_tro_sinh_san",
        "thụ tinh trong ống nghiệm": "vo_chong_ho_tro_sinh_san",
        "hỗ trợ sinh sản": "vo_chong_ho_tro_sinh_san",
        "phụ nữ độc thân": "phu_nu_doc_than",
        "cho tinh trùng": "nguoi_cho_tinh_trung_noan_phoi",
        "cho noãn": "nguoi_cho_tinh_trung_noan_phoi",
        "cho phôi": "nguoi_cho_tinh_trung_noan_phoi",
        "mang thai hộ nhân đạo": "mang_thai_ho_nhan_dao",
        "nhờ mang thai hộ": "mang_thai_ho_nhan_dao",
    },
    "tinh_trang_hon_nhan": {
        "ly thân": "ly_than",
    },
    "loai_chung_cu": {
        "xét nghiệm adn": "adn",
        "kết quả adn": "adn",
    },
    "tinh_trang_ghi_nhan": {
        "khai sinh ghi tên người khác": "giay_khai_sinh_ghi_nguoi_khac",
        "không được ghi nhận là cha": "chua_duoc_nhan_la_cha_me",
        "chưa được nhận là mẹ": "chua_duoc_nhan_la_cha_me",
        "đang được ghi nhận là cha": "dang_duoc_nhan_la_cha_me",
        "đang đứng tên cha": "dang_duoc_nhan_la_cha_me",
    },
    "huong_xac_dinh": {
        "không phải con ruột": "khong_phai_con_minh",
        "không phải là con mình": "khong_phai_con_minh",
        "xác định là con mình": "la_con_minh",
        "xác định con": "la_con_minh",
    },
    "doi_tuong_nhan": {
        "nhận cha": "cha",
        "tìm cha ruột": "cha",
        "nhận mẹ": "me",
        "tìm mẹ ruột": "me",
        "nhận con": "con",
        "con riêng": "con",
    },
    "doi_tuong_da_chet": {
        "đã chết": "co",
        "đã mất": "co",
        "qua đời": "co",
    },
    "chu_the_da_thanh_nien": {
        "20 tuổi": "co",
        "25 tuổi": "co",
        "đã thành niên": "co",
    },
    "nguoi_khac_khong_dong_y": {
        "không cần mẹ đồng ý": "me",
        "không cần cha đồng ý": "cha",
        "vợ không đồng ý": "vo",
        "chồng không đồng ý": "chong",
    },
    "nguoi_yeu_cau_thay": {
        "người thân thích": "nguoi_than_thich",
        "gia đình yêu cầu thay": "gia_dinh",
    },
    "vat_lieu_hien_tang": {
        "cho tinh trùng": "tinh_trung",
        "tinh trùng": "tinh_trung",
        "noãn": "noan",
        "phôi": "phoi",
    },
    "loai_vu_viec": {
        "tranh chấp ivf": "tranh_chap_ho_tro_sinh_san",
        "tranh chấp hỗ trợ sinh sản": "tranh_chap_ho_tro_sinh_san",
        "tranh chấp mang thai hộ": "tranh_chap_mang_thai_ho",
        "tranh chấp hỗ trợ sinh sản hoặc mang thai hộ": "tranh_chap_ho_tro_sinh_san_va_mang_thai_ho",
        "chưa giao con": "nhan_nuoi_khi_ben_nho_chet_hoac_mat_nang_luc",
        "chưa giao đứa trẻ": "nhan_nuoi_khi_ben_nho_chet_hoac_mat_nang_luc",
        "không nhận nuôi": "giam_ho_cap_duong_khi_khong_nhan_nuoi",
    },
    "tre_da_duoc_giao": {
        "chưa giao con": "chua",
        "chưa giao đứa trẻ": "chua",
    },
    "ben_mang_thai_ho_nhan_nuoi": {
        "không nhận nuôi": "khong",
    },
    "tinh_trang_tranh_chap": {
        "không có tranh chấp": "khong_co",
        "hai bên đồng thuận": "khong_co",
        "có tranh chấp": "co",
        "tranh chấp cha con": "co",
    },
    "kenh_yeu_cau": {
        "ubnd": "ho_tich",
        "hộ tịch": "ho_tich",
        "cơ quan đăng ký hộ tịch": "ho_tich",
        "khởi kiện": "toa_an",
        "ra tòa": "toa_an",
        "tòa án": "toa_an",
    },
    "nhom_nguoi_yeu_cau": {
        "người giám hộ": "nguoi_giam_ho",
        "cơ quan quản lý gia đình": "co_quan_gia_dinh",
        "cơ quan quản lý trẻ em": "co_quan_tre_em",
        "hội liên hiệp phụ nữ": "hoi_lien_hiep_phu_nu",
        "hội phụ nữ": "hoi_lien_hiep_phu_nu",
    },
    "doi_tuong_duoc_bao_ve": {
        "con chưa thành niên": "con_chua_thanh_nien",
        "con thành niên mất năng lực hành vi dân sự": "con_thanh_nien_mat_nang_luc_hanh_vi_dan_su",
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
    if not raw_text:
        return {}
    out: dict[str, Any] = {}
    for field in COMMON_TO_LEGAL_TERMS:
        val = resolve_term(field, raw_text)
        if val is not None:
            out[field] = val
    return out


__all__ = ["COMMON_TO_LEGAL_TERMS", "resolve_term", "resolve_many"]
