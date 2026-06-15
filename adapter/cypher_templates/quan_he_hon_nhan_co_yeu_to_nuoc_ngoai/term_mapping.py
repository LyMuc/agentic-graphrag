"""Ánh xạ thuật ngữ thông thường → param chuẩn cho topic quan_he_hon_nhan_co_yeu_to_nuoc_ngoai."""
from __future__ import annotations

import re
from typing import Any, Optional

COMMON_TO_LEGAL_TERMS: dict[str, dict[str, Any]] = {
    "pham_vi_bao_ve": {
        "tôn trọng và bảo vệ tại việt nam": "tai_viet_nam",
        "tại việt nam được tôn trọng": "tai_viet_nam",
        "người nước ngoài tại việt nam": "nguoi_nuoc_ngoai_tai_viet_nam",
        "công dân việt nam ở nước ngoài": "cong_dan_viet_nam_o_nuoc_ngoai",
        "bảo hộ công dân": "cong_dan_viet_nam_o_nuoc_ngoai",
        "chính phủ quy định chi tiết": "chinh_phu_quy_dinh_chi_tiet",
    },
    "khia_canh_bao_ve": {
        "quyền và nghĩa vụ": "quyen_nghia_vu",
        "quyền, nghĩa vụ": "quyen_nghia_vu",
    },
    "co_so_ap_dung": {
        "điều ước quốc tế": "dieu_uoc_quoc_te_co_quy_dinh_khac",
        "quy định khác": "dieu_uoc_quoc_te_co_quy_dinh_khac",
        "pháp luật việt nam dẫn chiếu": "phap_luat_viet_nam_dan_chieu",
        "điều ước quốc tế dẫn chiếu": "dieu_uoc_quoc_te_dan_chieu",
        "khi nào pháp luật nước ngoài được áp dụng": "tat_ca_truong_hop_dan_chieu",
        "dẫn chiếu trở lại": "phap_luat_nuoc_ngoai_dan_chieu_tro_lai",
        "dẫn chiếu về việt nam": "phap_luat_nuoc_ngoai_dan_chieu_tro_lai",
    },
    "loai_vu_viec": {
        "đăng ký hộ tịch": "dang_ky_ho_tich",
        "vụ việc tại tòa án": "vu_viec_tai_toa_an",
        "tòa án có thẩm quyền": "vu_viec_tai_toa_an",
        "khu vực biên giới": "ly_hon_tranh_chap_khu_vuc_bien_gioi",
        "công dân nước láng giềng": "ly_hon_tranh_chap_khu_vuc_bien_gioi",
    },
    "khia_canh_tham_quyen": {
        "cấp huyện nơi cư trú": "cap_toa_an",
        "tòa án cấp huyện": "cap_toa_an",
    },
    "nguon_giay_to": {
        "giấy tờ do nước ngoài": "co_quan_co_tham_quyen_nuoc_ngoai",
        "tài liệu nước ngoài": "co_quan_co_tham_quyen_nuoc_ngoai",
    },
    "khia_canh_hop_phap_hoa": {
        "có cần hợp pháp hóa lãnh sự": "co_phai_hop_phap_hoa",
        "hợp pháp hóa lãnh sự": "co_phai_hop_phap_hoa",
        "được miễn hợp pháp hóa": "truong_hop_mien",
    },
    "can_cu_mien": {
        "theo điều ước quốc tế": "dieu_uoc_quoc_te",
        "có đi có lại": "nguyen_tac_co_di_co_lai",
    },
    "nhu_cau_thi_hanh": {
        "có yêu cầu thi hành tại việt nam": "co_yeu_cau_thi_hanh_tai_viet_nam",
        "không có yêu cầu thi hành": "khong_yeu_cau_thi_hanh",
    },
    "khia_canh_ban_an": {
        "ghi vào sổ hộ tịch": "ghi_so_ho_tich",
        "ghi chú hộ tịch": "ghi_so_ho_tich",
    },
    "loai_quyet_dinh": {
        "quyết định của cơ quan khác": "quyet_dinh_co_quan_khac_nuoc_ngoai",
    },
    "nhom_chu_the": {
        "người việt nam với người mỹ": "cong_dan_viet_nam_voi_nguoi_nuoc_ngoai",
        "người việt nam với người pháp": "cong_dan_viet_nam_voi_nguoi_nuoc_ngoai",
        "người việt nam với người hàn": "cong_dan_viet_nam_voi_nguoi_nuoc_ngoai",
        "người nước ngoài thường trú tại việt nam": "hai_nguoi_nuoc_ngoai_thuong_tru_tai_viet_nam",
        "không thường trú tại việt nam": "cong_dan_viet_nam_khong_thuong_tru_tai_viet_nam",
        "hai công dân việt nam ở singapore": "hai_cong_dan_viet_nam_o_nuoc_ngoai",
        "hai công dân việt nam ở nước ngoài": "hai_cong_dan_viet_nam_o_nuoc_ngoai",
    },
    "noi_tien_hanh_ket_hon": {
        "đăng ký kết hôn tại việt nam": "co_quan_co_tham_quyen_viet_nam",
        "tại việt nam": "co_quan_co_tham_quyen_viet_nam",
    },
    "ben_can_xet": {
        "mỗi bên theo luật nước nào": "moi_ben",
        "luật nước nào": "moi_ben",
    },
    "hinh_thuc_ly_hon": {
        "thuận tình ly hôn": "thuan_tinh",
        "đơn phương ly hôn": "don_phuong",
        "một bên muốn ly hôn": "don_phuong",
    },
    "tinh_trang_noi_thuong_tru_chung": {
        "không có nơi thường trú chung": "khong",
        "thường trú chung tại singapore": "co",
        "cùng thường trú": "co",
    },
    "loai_tai_san": {
        "nhà ở nước ngoài": "bat_dong_san_o_nuoc_ngoai",
        "đất ở nước ngoài": "bat_dong_san_o_nuoc_ngoai",
        "bất động sản ở nước ngoài": "bat_dong_san_o_nuoc_ngoai",
        "căn nhà ở nước ngoài": "bat_dong_san_o_nuoc_ngoai",
    },
    "co_tranh_chap": {
        "tranh chấp về cha": "co",
        "tranh chấp về mẹ": "co",
        "tranh chấp về con": "co",
        "không có tranh chấp": "khong",
        "cơ quan đăng ký hộ tịch xác định": "khong",
        "tòa án xác định cha": "co",
        "tòa án xác định cha mẹ con": "co",
    },
    "khia_canh_cap_duong": {
        "cơ quan nào giải quyết cấp dưỡng": "co_quan_co_tham_quyen",
        "cơ quan giải quyết": "co_quan_co_tham_quyen",
    },
    "dang_quan_he": {
        "chế độ tài sản theo thỏa thuận": "che_do_tai_san_vo_chong_theo_thoa_thuan",
        "chung sống như vợ chồng": "chung_song_nhu_vo_chong_khong_dang_ky",
        "không đăng ký kết hôn": "chung_song_nhu_vo_chong_khong_dang_ky",
        "chưa đăng ký kết hôn": "chung_song_nhu_vo_chong_khong_dang_ky",
    },
    "yeu_cau_giai_quyet": {
        "chia tài sản khi chia tay": "chia_tai_san_khi_cham_dut",
        "chấm dứt chung sống": "chia_tai_san_khi_cham_dut",
        "chia tài sản khi chấm dứt": "chia_tai_san_khi_cham_dut",
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
