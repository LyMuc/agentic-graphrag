"""Ánh xạ thuật ngữ thông thường → param chuẩn cho topic quyen_nghia_vu_cha_me_con."""
from __future__ import annotations

import re
from typing import Any, Optional

COMMON_TO_LEGAL_TERMS: dict[str, dict[str, Any]] = {
    "khia_canh_bao_ve": {
        "được bảo vệ thế nào": "bao_ve_tong_quat",
        "nhà nước bảo vệ": "bao_ve_tong_quat",
        "ngoài giá thú": "binh_dang_khong_phu_thuoc_hon_nhan",
        "con riêng ngoài hôn nhân": "binh_dang_khong_phu_thuoc_hon_nhan",
        "chưa đăng ký kết hôn": "binh_dang_khong_phu_thuoc_hon_nhan",
        "quyền như con trong hôn nhân": "binh_dang_khong_phu_thuoc_hon_nhan",
        "cha mẹ nuôi": "quan_he_cha_me_nuoi_con_nuoi",
        "con nuôi": "quan_he_cha_me_nuoi_con_nuoi",
        "thỏa thuận về tài sản": "gioi_han_thoa_thuan",
        "thỏa thuận về tài sản của cha mẹ và con": "gioi_han_thoa_thuan",
    },
    "tinh_trang_hon_nhan_cua_cha_me": {
        "ngoài giá thú": "ngoai_hon_nhan",
        "con riêng ngoài hôn nhân": "ngoai_hon_nhan",
        "cha mẹ chưa đăng ký kết hôn": "khong_dang_ky_ket_hon",
        "chưa đăng ký kết hôn": "khong_dang_ky_ket_hon",
        "ly hôn": "ly_hon",
    },
    "nhom_nghia_vu_cha_me": {
        "đem con về nuôi": "trong_nom_nuoi_duong_cham_soc_bao_ve",
        "giành lại việc chăm con": "trong_nom_nuoi_duong_cham_soc_bao_ve",
        "trông nom": "trong_nom_nuoi_duong_cham_soc_bao_ve",
        "nuôi dưỡng": "trong_nom_nuoi_duong_cham_soc_bao_ve",
        "ly thân": "trong_nom_nuoi_duong_cham_soc_bao_ve",
        "phân biệt con trai con gái": "khong_phan_biet_doi_xu",
        "phân biệt vì sinh ngoài hôn nhân": "khong_phan_biet_doi_xu",
        "bắt làm nặng": "khong_lam_dung_suc_lao_dong",
        "bóc lột sức lao động": "khong_lam_dung_suc_lao_dong",
        "lao động nặng": "khong_lam_dung_suc_lao_dong",
        "xúi giục": "khong_xui_giuc_ep_buoc_trai_phap_luat",
        "ép làm việc trái pháp luật": "khong_xui_giuc_ep_buoc_trai_phap_luat",
        "ép lao động nặng đồng thời xúi giục làm trái pháp luật": "cac_hanh_vi_bi_cam_khoan_4",
        "lao động nặng hoặc xúi giục": "cac_hanh_vi_bi_cam_khoan_4",
    },
    "boi_canh_gia_dinh": {
        "ly thân": "ly_than",
        "ly hôn": "ly_hon",
    },
    "nhom_quyen_nghia_vu_cua_con": {
        "sang thăm bố": "song_chung_duoc_cham_soc",
        "sống với bố mẹ": "song_chung_duoc_cham_soc",
        "tự chọn nghề": "tu_do_nghe_nghiep_noi_cu_tru",
        "tự chọn chỗ ở": "tu_do_nghe_nghiep_noi_cu_tru",
        "nghề nghiệp và nơi cư trú": "tu_do_nghe_nghiep_noi_cu_tru",
    },
    "chieu_cham_soc_nuoi_duong": {
        "con chăm bố mẹ già yếu": "con_doi_voi_cha_me",
        "con chăm sóc cha mẹ": "con_doi_voi_cha_me",
        "các con cùng nuôi bố mẹ": "cac_con_doi_voi_cha_me",
        "nhiều con": "cac_con_doi_voi_cha_me",
        "bố mẹ ngang nhau chăm con": "cha_me_doi_voi_con",
        "cha mẹ ngang nhau": "cha_me_doi_voi_con",
    },
    "hoan_canh_can_cham_soc": {
        "bố bị liệt": "cha_me_khuyet_tat",
        "bị liệt": "cha_me_khuyet_tat",
        "già yếu": "cha_me_gia_yeu",
        "ốm đau": "cha_me_om_dau",
        "mất năng lực hành vi": "cha_me_mat_nang_luc_hanh_vi",
    },
    "khia_canh_giao_duc": {
        "ép con học ngành": "huong_dan_ton_trong_chon_nghe",
        "ép con theo học ngành": "huong_dan_ton_trong_chon_nghe",
        "chọn nghề thay con": "huong_dan_ton_trong_chon_nghe",
        "nhờ cơ quan": "de_nghi_ho_tro_khi_kho_khan",
        "nhà trường hỗ trợ": "de_nghi_ho_tro_khi_kho_khan",
        "không tự giáo dục": "de_nghi_ho_tro_khi_kho_khan",
        "giáo dục và tạo điều kiện học tập": "giao_duc_tao_dieu_kien_hoc_tap",
    },
    "loai_van_de_dai_dien": {
        "ai đại diện": "nguoi_dai_dien_theo_phap_luat",
        "đại diện theo pháp luật": "nguoi_dai_dien_theo_phap_luat",
        "mua đồ dùng thiết yếu": "giao_dich_nhu_cau_thiet_yeu",
        "đồ dùng thiết yếu": "giao_dich_nhu_cau_thiet_yeu",
        "bán nhà": "giao_dich_tai_san_quan_trong",
        "bán đất": "giao_dich_tai_san_quan_trong",
        "bán nhà đứng tên con": "giao_dich_tai_san_quan_trong",
        "đứng tên con": "giao_dich_tai_san_quan_trong",
    },
    "loai_tai_san_giao_dich": {
        "bán nhà": "bat_dong_san",
        "bán đất": "bat_dong_san",
        "đồ dùng thiết yếu": "nhu_cau_thiet_yeu",
    },
    "chu_the_thuc_hien": {
        "mẹ một mình": "me",
        "cả bố và mẹ": "ca_cha_va_me",
        "cả hai cha mẹ": "ca_cha_va_me",
        "thỏa thuận của cha mẹ": "ca_cha_va_me",
    },
    "khia_canh_boi_thuong": {
        "có phải bồi thường": "co_phai_boi_thuong",
        "có trách nhiệm bồi thường": "co_phai_boi_thuong",
        "cha mẹ có phải đền": "co_phai_boi_thuong",
    },
    "tinh_trang_cua_con_gay_thiet_hai": {
        "12 tuổi": "chua_thanh_nien",
        "con nhỏ": "chua_thanh_nien",
        "chưa thành niên": "chua_thanh_nien",
    },
    "khia_canh_nuoi_con_nuoi": {
        "kể từ khi nhận nuôi": "thoi_diem_phat_sinh",
        "xác lập nuôi con nuôi": "thoi_diem_phat_sinh",
        "thời điểm nào": "thoi_diem_phat_sinh",
        "chấm dứt nuôi con nuôi": "thoi_diem_cham_dut",
        "khôi phục quyền cha mẹ đẻ": "khoi_phuc_quyen_nghia_vu_cha_me_de",
    },
    "chu_the_quan_he_nuoi_con_nuoi": {
        "cha nuôi": "cha_me_nuoi_va_con_nuoi",
        "mẹ nuôi": "cha_me_nuoi_va_con_nuoi",
        "con nuôi": "cha_me_nuoi_va_con_nuoi",
    },
    "loai_quan_he_gia_dinh_mo_rong": {
        "cha dượng": "cha_duong_me_ke_va_con_rieng",
        "mẹ kế": "cha_duong_me_ke_va_con_rieng",
        "con riêng của vợ": "cha_duong_me_ke_va_con_rieng",
        "con riêng của chồng": "cha_duong_me_ke_va_con_rieng",
        "con dâu": "con_dau_re_va_cha_me_vo_chong",
        "con rể": "con_dau_re_va_cha_me_vo_chong",
        "cha mẹ chồng": "con_dau_re_va_cha_me_vo_chong",
        "cha mẹ vợ": "con_dau_re_va_cha_me_vo_chong",
    },
    "tinh_trang_song_chung": {
        "sống chung": "co_song_chung",
        "cùng sống chung": "co_song_chung",
        "ở chung": "co_song_chung",
        "không sống chung": "khong_song_chung",
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
