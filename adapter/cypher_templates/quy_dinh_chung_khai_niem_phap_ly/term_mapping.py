"""Ánh xạ thuật ngữ thông thường → param chuẩn cho topic quy_dinh_chung_khai_niem_phap_ly."""
from __future__ import annotations

import re
from typing import Any, Optional

COMMON_TO_LEGAL_TERMS: dict[str, dict[str, Any]] = {
    "khia_canh_nguyen_tac": {
        "nguyên tắc cơ bản": "liet_ke_tat_ca",
        "nguyên tắc hôn nhân gia đình": "liet_ke_tat_ca",
        "một vợ một chồng": "mot_vo_mot_chong",
        "chung thủy một vợ một chồng": "mot_vo_mot_chong",
        "tự nguyện": "tu_nguyen_tien_bo",
        "tiến bộ": "tu_nguyen_tien_bo",
        "vợ chồng bình đẳng": "vo_chong_binh_dang",
    },
    "chu_the_trach_nhiem": {
        "nhà nước và xã hội có trách nhiệm gì": "tat_ca",
        "cơ quan nào thống nhất quản lý": "chinh_phu",
        "ai thống nhất quản lý": "chinh_phu",
        "bộ": "bo_co_quan_ngang_bo",
        "cơ quan ngang bộ": "bo_co_quan_ngang_bo",
        "ủy ban nhân dân": "uy_ban_nhan_dan_va_co_quan_khac",
        "ubnd": "uy_ban_nhan_dan_va_co_quan_khac",
    },
    "khia_canh_trach_nhiem": {
        "thống nhất quản lý nhà nước": "thong_nhat_quan_ly_nha_nuoc",
        "tuyên truyền pháp luật": "tuyen_truyen_xoa_bo_tap_quan_lac_hau",
        "phổ biến pháp luật": "tuyen_truyen_xoa_bo_tap_quan_lac_hau",
    },
    "nhom_hanh_vi": {
        "hành vi bị cấm": "tat_ca",
        "các điều cấm": "tat_ca",
        "ngoại tình": "vi_pham_mot_vo_mot_chong",
        "vi phạm một vợ một chồng": "vi_pham_mot_vo_mot_chong",
        "tảo hôn": "tao_hon_cuong_ep_lua_doi_can_tro_ket_hon",
        "ép cưới": "tao_hon_cuong_ep_lua_doi_can_tro_ket_hon",
        "lừa cưới": "tao_hon_cuong_ep_lua_doi_can_tro_ket_hon",
        "cản cưới": "tao_hon_cuong_ep_lua_doi_can_tro_ket_hon",
        "kết hôn giả": "ket_hon_ly_hon_gia_tao",
        "ly hôn giả": "ket_hon_ly_hon_gia_tao",
    },
    "dang_quan_he_thuc_te": {
        "sống chung": "chung_song_nhu_vo_chong",
        "ăn ở như vợ chồng": "chung_song_nhu_vo_chong",
        "chung sống như vợ chồng": "chung_song_nhu_vo_chong",
        "chỉ qua lại": "qua_lai_tinh_cam",
        "đang tìm hiểu": "qua_lai_tinh_cam",
        "có quan hệ tình cảm": "qua_lai_tinh_cam",
    },
    "tinh_trang_hon_nhan": {
        "ly thân": "ly_than_chua_ly_hon",
        "đang ly thân nhưng chưa ly hôn": "ly_than_chua_ly_hon",
        "đã có bản án ly hôn": "da_ly_hon",
        "đã ly hôn": "da_ly_hon",
        "đang có vợ": "dang_co_vo_chong",
        "đang có chồng": "dang_co_vo_chong",
        "chưa ly hôn": "dang_co_vo_chong",
    },
    "loai_quan_he": {
        "cận huyết": "ho_trong_pham_vi_ba_doi",
        "họ hàng ba đời": "ho_trong_pham_vi_ba_doi",
        "phạm vi ba đời": "ho_trong_pham_vi_ba_doi",
        "dòng máu trực hệ": "cung_dong_mau_truc_he",
        "trực hệ": "cung_dong_mau_truc_he",
        "cha mẹ là đời mấy": "cha_me_doi_thu_nhat",
        "anh chị em ruột": "anh_chi_em_doi_thu_hai",
        "cùng cha khác mẹ": "anh_chi_em_doi_thu_hai",
        "cùng mẹ khác cha": "anh_chi_em_doi_thu_hai",
        "con chú bác cô cậu dì": "anh_chi_em_ho_doi_thu_ba",
        "anh chị em họ": "anh_chi_em_ho_doi_thu_ba",
    },
    "khia_canh_ba_doi": {
        "trong phạm vi mấy đời": "so_doi_bi_cam",
        "cấm mấy đời": "so_doi_bi_cam",
        "gồm những ai": "liet_ke_nguoi_trong_ba_doi",
        "ba đời gồm ai": "liet_ke_nguoi_trong_ba_doi",
    },
    "noi_dung_phap_ly": {
        "kết hôn là gì": "ket_hon",
        "kết hôn trái pháp luật": "ket_hon_trai_phap_luat",
        "cưới trái luật": "ket_hon_trai_phap_luat",
        "cấp dưỡng": "cap_duong",
        "chu cấp theo luật": "cap_duong",
        "thời kỳ hôn nhân": "thoi_ky_hon_nhan",
        "thời kì hôn nhân": "thoi_ky_hon_nhan",
        "chung sống như vợ chồng là gì": "chung_song_nhu_vo_chong",
        "ly hôn là gì": "ly_hon",
        "tập quán hôn nhân": "ap_dung_tap_quan",
        "áp dụng phong tục": "ap_dung_tap_quan",
        "bộ luật dân sự": "ap_dung_phap_luat_lien_quan",
        "luật khác có liên quan": "ap_dung_phap_luat_lien_quan",
    },
    "khia_canh_khai_niem": {
        "bắt đầu từ khi nào": "thoi_diem_bat_dau",
        "tính từ ngày nào": "thoi_diem_bat_dau",
        "chấm dứt khi nào": "thoi_diem_ket_thuc",
        "kết thúc khi nào": "thoi_diem_ket_thuc",
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
            if field == "dang_quan_he_thuc_te" and pattern == "sống chung":
                if "ngoại tình" in norm and "chung sống" not in norm and "như vợ chồng" not in norm:
                    continue
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
