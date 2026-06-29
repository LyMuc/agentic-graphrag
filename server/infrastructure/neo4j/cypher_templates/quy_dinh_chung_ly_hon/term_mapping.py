"""Ánh xạ thuật ngữ thông thường → param chuẩn cho topic quy_dinh_chung_ly_hon."""
from __future__ import annotations

import re
from typing import Any, Optional

COMMON_TO_LEGAL_TERMS: dict[str, dict[str, Any]] = {
    "chu_the_yeu_cau": {
        "vợ xin ly hôn": "vo",
        "người vợ yêu cầu": "vo",
        "chồng xin ly hôn": "chong",
        "anh chồng đơn phương": "chong",
        "hai vợ chồng cùng đồng ý": "ca_hai",
        "cả hai cùng ký": "ca_hai",
        "cha mẹ yêu cầu thay": "cha_me_nguoi_than_thich",
        "bố mẹ yêu cầu": "cha_me_nguoi_than_thich",
        "người thân yêu cầu": "cha_me_nguoi_than_thich",
    },
    "tinh_trang_vo_con": {
        "mang thai": "dang_co_thai",
        "có bầu": "dang_co_thai",
        "mới sinh": "dang_sinh_con",
        "vừa sinh con": "dang_sinh_con",
        "con 5 tháng": "dang_nuoi_con_duoi_12_thang",
        "con 6 tháng": "dang_nuoi_con_duoi_12_thang",
        "con dưới một tuổi": "dang_nuoi_con_duoi_12_thang",
    },
    "nang_luc_va_bao_luc": {
        "bệnh tâm thần": "mat_nang_luc_kem_bao_luc_nghiem_trong",
        "không nhận thức": "mat_nang_luc_kem_bao_luc_nghiem_trong",
        "bị đánh": "bao_luc_thong_thuong",
        "bạo hành": "bao_luc_thong_thuong",
    },
    "boi_canh_yeu_cau": {
        "quốc tịch nước ngoài": "co_yeu_to_nuoc_ngoai",
        "chồng ở nước ngoài": "co_yeu_to_nuoc_ngoai",
        "tài sản ở nước ngoài": "co_yeu_to_nuoc_ngoai",
    },
    "khia_canh_quyen": {
        "ai có quyền": "chu_the_co_quyen",
        "chồng không được đơn phương": "han_che_quyen_cua_chong",
        "cấm chồng ly hôn": "han_che_quyen_cua_chong",
    },
    "giai_doan": {
        "hòa giải ở xã": "hoa_giai_o_co_so",
        "hòa giải ở phường": "hoa_giai_o_co_so",
        "hòa giải cơ sở": "hoa_giai_o_co_so",
        "hòa giải tại tòa": "hoa_giai_tai_toa",
        "hòa giải sau thụ lý": "hoa_giai_tai_toa",
        "hòa giải có bắt buộc": "phan_biet_co_so_va_tai_toa",
        "tòa nhận đơn": "thu_ly_don",
        "thụ lý đơn": "thu_ly_don",
        "nộp đơn lâu chưa giải quyết": "da_nop_don_cham_giai_quyet",
        "tòa hẹn nhiều lần": "da_nop_don_cham_giai_quyet",
    },
    "hinh_thuc_ly_hon": {
        "thuận tình": "thuan_tinh",
        "cả hai đồng ý ly hôn": "thuan_tinh",
        "một bên": "don_phuong",
        "đơn phương": "don_phuong",
    },
    "dang_ky_ket_hon": {
        "không đăng ký kết hôn": "khong",
        "không có giấy kết hôn": "khong",
    },
    "khia_canh_hoa_giai": {
        "có bắt buộc hòa giải": "co_bat_buoc_hay_khong",
        "tòa chậm giải quyết": "tinh_trang_cham_giai_quyet",
    },
    "muc_do_thoa_thuan": {
        "đã thống nhất hết": "day_du",
        "không thỏa thuận được": "khong_thoa_thuan_duoc",
        "thỏa thuận bất lợi cho vợ": "thoa_thuan_khong_bao_dam",
    },
    "noi_dung_thoa_thuan": {
        "chia tài sản": "tai_san",
        "nuôi con": "con_chung",
        "chăm sóc con": "con_chung",
    },
    "tu_nguyen": {
        "tự nguyện": "co",
        "không bị ép": "co",
    },
    "khia_canh_thuan_tinh": {
        "là gì": "khai_niem",
        "điều kiện công nhận": "dieu_kien_cong_nhan",
        "khi nào công nhận": "dieu_kien_cong_nhan",
    },
    "y_chi_vo_chong": {
        "hai bên đồng ý": "ca_hai_dong_y",
        "chồng không chịu": "mot_ben_khong_dong_y",
        "vợ không đồng ý": "mot_ben_khong_dong_y",
    },
    "khia_canh_hinh_thuc": {
        "điều kiện tiến hành ly hôn": "dieu_kien_tien_hanh",
        "ai đứng tên đơn": "chu_the_dung_ten_yeu_cau",
        "luật sư ghi tên": "chu_the_dung_ten_yeu_cau",
    },
    "co_con_duoi_12_thang": {
        "con 5 tháng": "co",
        "con 6 tháng": "co",
        "dưới một tuổi": "co",
    },
    "co_tranh_chap_tai_san_con": {
        "tranh chấp": "co",
        "không thống nhất": "co",
    },
    "boi_canh_to_tung": {
        "luật sư làm đơn": "luat_su_soan_don",
        "luật sư soạn đơn": "luat_su_soan_don",
    },
    "can_cu": {
        "ngoại tình": "ngoai_tinh",
        "có người khác": "ngoai_tinh",
        "cờ bạc": "co_bac_ruou_che_bo_mac",
        "rượu chè": "co_bac_ruou_che_bo_mac",
        "bỏ mặc gia đình": "co_bac_ruou_che_bo_mac",
        "đánh đập": "bao_luc_gia_dinh",
        "bạo hành": "bao_luc_gia_dinh",
        "vi phạm nghiêm trọng": "vi_pham_nghiem_trong_quyen_nghia_vu",
    },
    "chu_the_don_phuong": {
        "vợ xin ly hôn": "vo",
        "chồng xin ly hôn": "chong",
    },
    "hau_qua_hon_nhan": {
        "hôn nhân trầm trọng": "tinh_trang_tram_trong",
        "không thể sống chung": "doi_song_khong_the_keo_dai",
        "mục đích hôn nhân không đạt": "muc_dich_khong_dat",
    },
    "boi_canh_hon_nhan": {
        "ly thân": "dang_ly_than",
        "chuyển về nhà ngoại": "dang_ly_than",
        "vẫn sống chung": "dang_song_chung",
    },
    "tinh_trang": {
        "tòa án tuyên bố mất tích": "da_bi_toa_tuyen_bo_mat_tich",
        "biệt tích hơn 2 năm": "biet_tich_tu_hai_nam_chua_tuyen_bo",
        "biệt tích 3 năm": "biet_tich_tu_hai_nam_chua_tuyen_bo",
        "không liên lạc được": "khong_lien_lac_chua_ro_thoi_gian",
        "bỏ đi không có tin": "khong_lien_lac_chua_ro_thoi_gian",
        "đang mất tích": "mat_tich_theo_cach_noi_thong_thuong",
    },
    "da_thong_bao_tim_kiem": {
        "đăng báo tìm kiếm": "co",
        "thông báo tìm người": "co",
    },
    "tinh_huong": {
        "bản án có hiệu lực": "ban_an_quyet_dinh_co_hieu_luc",
        "quyết định ly hôn có hiệu lực": "ban_an_quyet_dinh_co_hieu_luc",
        "đang làm thủ tục": "dang_lam_thu_tuc",
        "đang chờ ly hôn": "dang_lam_thu_tuc",
        "ly thân": "ly_than",
        "xé giấy kết hôn": "xe_giay_dang_ky_ket_hon",
        "hủy giấy đăng ký kết hôn": "xe_giay_dang_ky_ket_hon",
        "vợ chết": "vo_chong_chet",
        "chồng chết": "vo_chong_chet",
    },
    "hanh_vi_trong_khi_cho": {
        "chung sống với người khác": "chung_song_voi_nguoi_khac",
        "sống với người khác khi đang ly hôn": "chung_song_voi_nguoi_khac",
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
