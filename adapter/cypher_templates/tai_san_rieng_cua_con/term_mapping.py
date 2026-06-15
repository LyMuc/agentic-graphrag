"""Ánh xạ thuật ngữ thông thường → param chuẩn cho topic tai_san_rieng_cua_con."""
from __future__ import annotations

import re
from typing import Any, Optional

COMMON_TO_LEGAL_TERMS: dict[str, dict[str, Any]] = {
    "khia_canh_tai_san": {
        "có tài sản riêng": "quyen_co_tai_san_rieng",
        "quyền có tài sản": "quyen_co_tai_san_rieng",
        "gồm những gì": "liet_ke_thanh_phan",
        "bao gồm loại nào": "liet_ke_thanh_phan",
        "có phải tài sản riêng không": "xac_dinh_co_phai_tai_san_rieng",
    },
    "loai_tai_san": {
        "thừa kế riêng": "tai_san_thua_ke_rieng",
        "ông bà để lại riêng": "tai_san_thua_ke_rieng",
        "tặng cho riêng": "tai_san_tang_cho_rieng",
        "cho riêng": "tai_san_tang_cho_rieng",
        "biếu riêng": "tai_san_tang_cho_rieng",
        "tiền lương": "thu_nhap_lao_dong",
        "tiền công": "thu_nhap_lao_dong",
        "tự đi làm kiếm được": "thu_nhap_lao_dong",
        "hoa lợi": "hoa_loi_loi_tuc",
        "lợi tức": "hoa_loi_loi_tuc",
        "tiền lãi": "hoa_loi_loi_tuc",
        "tiền cho thuê phát sinh": "hoa_loi_loi_tuc",
        "thu nhập hợp pháp khác": "thu_nhap_hop_phap_khac",
        "tài sản mua từ tài sản riêng": "tai_san_hinh_thanh_tu_tai_san_rieng",
        "tài sản tạo từ tài sản riêng": "tai_san_hinh_thanh_tu_tai_san_rieng",
        "nhà, đất": "bat_dong_san",
        "nhà đất": "bat_dong_san",
        "quyền sử dụng đất": "bat_dong_san",
        "xe máy": "dong_san_phai_dang_ky",
        "ô tô": "dong_san_phai_dang_ky",
        "xe đứng tên": "dong_san_phai_dang_ky",
        "đất": "bat_dong_san",
        "chuyển nhượng đất": "bat_dong_san",
    },
    "nhom_tuoi": {
        "15 tuổi": "tu_du_15_chua_thanh_nien",
        "16 tuổi": "tu_du_15_chua_thanh_nien",
        "17 tuổi": "tu_du_15_chua_thanh_nien",
        "chưa đủ 18": "tu_du_15_chua_thanh_nien",
        "đã thành niên": "da_thanh_nien",
        "đủ 18 tuổi": "da_thanh_nien",
        "đã thành niên mất năng lực hành vi dân sự": "da_thanh_nien",
    },
    "song_chung_voi_cha_me": {
        "sống chung": "co",
        "ở cùng cha mẹ": "co",
    },
    "khia_canh_dong_gop": {
        "chăm lo đời sống chung": "cham_lo_doi_song_chung",
        "chi tiêu thiết yếu": "dong_gop_nhu_cau_thiet_yeu",
        "nhu cầu thiết yếu": "dong_gop_nhu_cau_thiet_yeu",
        "nhu cầu của gia đình": "dong_gop_nhu_cau_gia_dinh",
    },
    "lua_chon_quan_ly": {
        "tự quản lý": "tu_quan_ly",
        "nhờ cha mẹ giữ": "nho_cha_me_quan_ly",
        "nhờ cha mẹ quản lý": "nho_cha_me_quan_ly",
    },
    "tinh_trang_con": {
        "dưới 15 tuổi": "duoi_15_tuoi",
        "chưa đủ 15": "duoi_15_tuoi",
        "mất năng lực hành vi dân sự": "mat_nang_luc_hanh_vi_dan_su",
        "khôi phục năng lực hành vi dân sự đầy đủ": "khoi_phuc_nang_luc_hanh_vi_dan_su_day_du",
    },
    "khia_canh_quan_ly": {
        "ai quản lý": "ai_quan_ly",
        "ủy quyền ông bà": "uy_quyen_nguoi_khac",
        "ủy quyền người khác quản lý": "uy_quyen_nguoi_khac",
        "giao lại": "giao_lai_khi_nao",
        "trả lại tài sản": "giao_lai_khi_nao",
        "thỏa thuận giao sau": "thoa_thuan_khac",
        "thỏa thuận giao thời điểm khác": "thoa_thuan_khac",
        "cha mẹ có phải quản lý không": "cha_me_co_quan_ly_khong",
        "người tặng cho chỉ định": "co_the_chi_dinh_nguoi_quan_ly",
        "di chúc chỉ định": "co_the_chi_dinh_nguoi_quan_ly",
        "giao lại cho người giám hộ": "giao_lai_cho_nguoi_giam_ho",
    },
    "truong_hop_quan_ly": {
        "đang do người khác giám hộ": "con_dang_duoc_nguoi_khac_giam_ho",
        "con chưa thành niên đang được ông bà giám hộ": "con_dang_duoc_nguoi_khac_giam_ho",
        "giao cho ông bà giám hộ": "con_dang_duoc_nguoi_khac_giam_ho",
        "người tặng cho chỉ định": "nguoi_tang_cho_hoac_de_lai_di_chuc_chi_dinh",
        "di chúc chỉ định": "nguoi_tang_cho_hoac_de_lai_di_chuc_chi_dinh",
        "cha mẹ đang quản lý, sau đó con đã thành niên mất năng lực": "chuyen_giao_sang_nguoi_giam_ho",
        "con đã thành niên mất năng lực và được giao người giám hộ": "chuyen_giao_sang_nguoi_giam_ho",
    },
    "nguoi_dang_quan_ly": {
        "cha mẹ định đoạt": "cha_me",
        "cha mẹ bán": "cha_me",
        "người giám hộ định đoạt": "nguoi_giam_ho",
    },
    "nguoi_thuc_hien": {
        "người giám hộ định đoạt": "nguoi_giam_ho",
        "người giám hộ có quyền": "nguoi_giam_ho",
    },
    "khia_canh_dinh_doat": {
        "vì lợi ích của con": "vi_loi_ich_cua_con",
        "xem xét ý kiến của con": "xem_xet_nguyen_vong",
        "xem xét nguyện vọng của con": "xem_xet_nguyen_vong",
        "đồng ý bằng giấy": "co_can_dong_y_bang_van_ban",
        "chấp thuận bằng văn bản": "co_can_dong_y_bang_van_ban",
        "ai thực hiện": "ai_thuc_hien",
        "người giám hộ có quyền không": "nguoi_giam_ho_co_quyen_khong",
    },
    "hinh_thuc_dinh_doat": {
        "mở quán": "dung_de_kinh_doanh",
        "góp vốn": "dung_de_kinh_doanh",
        "dùng tiền kinh doanh": "dung_de_kinh_doanh",
        "dùng tài sản kinh doanh": "dung_de_kinh_doanh",
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
