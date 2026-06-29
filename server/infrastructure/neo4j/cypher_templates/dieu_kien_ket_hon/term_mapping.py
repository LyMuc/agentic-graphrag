"""Ánh xạ thuật ngữ thông thường → param chuẩn cho topic dieu_kien_ket_hon."""
from __future__ import annotations

import re
from typing import Any, Optional

COMMON_TO_LEGAL_TERMS: dict[str, dict[str, Any]] = {
    "gioi_tinh_hai_ben": {
        "hôn nhân đồng tính": "cung_gioi",
        "đồng giới": "cung_gioi",
        "cùng giới": "cung_gioi",
        "hai nam": "cung_gioi",
        "hai nữ": "cung_gioi",
        "nam và nữ": "khac_gioi",
        "khác giới": "khac_gioi",
    },
    "khia_canh_cung_gioi": {
        "có bị cấm không": "co_bi_cam",
        "hành vi cấm": "co_bi_cam",
        "có chấp nhận": "co_duoc_thua_nhan",
        "có công nhận": "co_duoc_thua_nhan",
        "có thừa nhận": "co_duoc_thua_nhan",
        "chấp nhận hôn nhân đồng giới": "co_duoc_thua_nhan",
    },
    "gioi_tinh_nguoi_can_xet": {
        "con trai": "nam",
        "con gái": "nu",
        "nam nữ đều": "ca_hai",
        "cả hai cùng tuổi": "ca_hai",
    },
    "dang_du_lieu_tuoi": {
        "18 tuổi": "tuoi_hien_tai",
        "20 tuổi": "tuoi_hien_tai",
        "sinh năm": "nam_sinh_va_nam_xet",
        "nam nữ đều 18": "ca_hai_cung_tuoi",
    },
    "khia_canh_tuoi": {
        "sinh năm bao nhiêu": "nam_sinh_du_dieu_kien",
        "bao nhiêu tuổi": "nguong_tuoi",
        "đã đủ tuổi chưa": "da_du_tuoi",
        "đủ tuổi chưa": "da_du_tuoi",
        "có được kết hôn không": "da_du_tuoi",
    },
    "pham_vi_liet_ke": {
        "trường hợp nào bị cấm": "tat_ca_a_den_d",
        "dù không huyết thống": "khong_huyet_thong",
        "không có huyết thống": "khong_huyet_thong",
        "đã có vợ": "dang_co_vo_chong",
        "đã có chồng": "dang_co_vo_chong",
        "chưa ly hôn": "dang_co_vo_chong",
        "tảo hôn": "tao_hon_cuong_ep_lua_doi_can_tro",
        "lấy vợ lấy chồng sớm": "tao_hon_cuong_ep_lua_doi_can_tro",
        "cưỡng ép kết hôn": "tao_hon_cuong_ep_lua_doi_can_tro",
        "ép cưới": "tao_hon_cuong_ep_lua_doi_can_tro",
        "lừa cưới": "tao_hon_cuong_ep_lua_doi_can_tro",
        "lừa dối kết hôn": "tao_hon_cuong_ep_lua_doi_can_tro",
        "cản cưới": "tao_hon_cuong_ep_lua_doi_can_tro",
        "gia đình cấm cưới": "tao_hon_cuong_ep_lua_doi_can_tro",
        "kết hôn giả": "gia_tao",
        "cưới giả": "gia_tao",
    },
    "khia_canh_cam": {
        "trường hợp nào": "liet_ke",
        "liệt kê": "liet_ke",
        "có bị cấm không": "co_bi_cam",
        "tại sao": "giai_thich",
    },
    "loai_quan_he_huyet_thong": {
        "hôn nhân cận huyết": "can_huyet_khong_ro",
        "cận huyết": "can_huyet_khong_ro",
        "ba đời": "ho_trong_pham_vi_ba_doi",
        "trong phạm vi ba đời": "ho_trong_pham_vi_ba_doi",
        "dòng máu trực hệ": "cung_dong_mau_truc_he",
        "trực hệ": "cung_dong_mau_truc_he",
        "anh chị em ruột": "anh_chi_em_cung_cha_me",
        "anh em cùng cha mẹ": "anh_chi_em_cung_cha_me",
        "anh em cùng cha khác mẹ": "anh_chi_em_cung_cha_khac_me",
        "anh em cùng mẹ khác cha": "anh_chi_em_cung_me_khac_cha",
        "con chú": "anh_chi_em_con_chu_bac_co_cau_di",
        "con bác": "anh_chi_em_con_chu_bac_co_cau_di",
        "con cô": "anh_chi_em_con_chu_bac_co_cau_di",
        "con cậu": "anh_chi_em_con_chu_bac_co_cau_di",
        "con dì": "anh_chi_em_con_chu_bac_co_cau_di",
        "con riêng của bố": "con_rieng_cua_bo",
        "hai cháu nội cùng ông": "hai_chau_noi_cung_goc",
        "cùng một gốc": "hai_chau_noi_cung_goc",
    },
    "khia_canh_ba_doi": {
        "có được kết hôn": "co_duoc_ket_hon",
        "có được không": "co_duoc_ket_hon",
        "ba đời tính thế nào": "cach_tinh_ba_doi",
        "phải qua mấy đời": "phai_qua_may_doi",
    },
    "co_chung_goc_sinh_ra": {
        "cùng ông": "co",
        "cùng bà": "co",
        "cùng một gốc": "co",
    },
    "loai_quan_he_bi_cam": {
        "cha nuôi": "cha_me_nuoi_con_nuoi",
        "mẹ nuôi": "cha_me_nuoi_con_nuoi",
        "cha mẹ nuôi với con nuôi": "cha_me_nuoi_con_nuoi",
        "cha dượng với con riêng": "cha_duong_con_rieng_cua_vo",
        "cha dượng": "cha_duong_con_rieng_cua_vo",
        "con riêng của vợ": "cha_duong_con_rieng_cua_vo",
        "mẹ kế với con riêng": "me_ke_con_rieng_cua_chong",
        "mẹ kế": "me_ke_con_rieng_cua_chong",
        "con riêng của chồng": "me_ke_con_rieng_cua_chong",
        "cha chồng với con dâu": "cha_chong_con_dau",
        "cha chồng": "cha_chong_con_dau",
        "con dâu": "cha_chong_con_dau",
        "mẹ vợ với con rể": "me_vo_con_re",
        "mẹ vợ": "me_vo_con_re",
        "con rể": "me_vo_con_re",
    },
    "khia_canh_quan_he_bi_cam": {
        "được không": "co_duoc_ket_hon",
        "có bị cấm": "co_bi_cam",
        "căn cứ nào": "xac_dinh_can_cu",
    },
    "loai_quan_he_thong_gia": {
        "em trai chồng với em gái vợ": "em_trai_chong_em_gai_vo",
        "em trai chồng": "em_trai_chong_em_gai_vo",
        "em gái vợ": "em_trai_chong_em_gai_vo",
        "em chồng với anh vợ": "em_chong_anh_vo",
        "em chồng": "em_chong_anh_vo",
        "anh vợ": "em_chong_anh_vo",
        "chị dâu": "thong_gia_khac",
        "anh rể": "thong_gia_khac",
        "thông gia": "thong_gia_khac",
    },
    "co_quan_he_huyet_thong_thuc_te": {
        "không cùng máu": "khong",
        "chỉ là thông gia": "khong",
        "có chung ông bà": "co",
        "cùng một gốc": "co",
    },
    "khia_canh_thong_gia": {
        "có cấm": "co_bi_cam",
        "vi phạm": "co_bi_cam",
        "điều kiện gì": "dieu_kien_can_dap_ung",
        "ba đời": "kiem_tra_ba_doi",
    },
    "tinh_trang_dang_ky": {
        "chỉ có đám cưới": "chi_co_dam_cuoi",
        "lễ cưới nhưng chưa đăng ký": "chi_co_dam_cuoi",
        "đám cưới": "chi_co_dam_cuoi",
        "lễ cưới": "chi_co_dam_cuoi",
        "đã đăng ký": "da_dang_ky_hop_le",
        "có giấy kết hôn": "da_dang_ky_hop_le",
        "chưa đăng ký": "chua_dang_ky",
    },
    "khia_canh_xac_lap": {
        "phải có đám cưới": "dam_cuoi_co_du_khong",
        "đám cưới có đủ": "dam_cuoi_co_du_khong",
        "vợ chồng hợp pháp khi nào": "khi_nao_la_vo_chong_hop_phap",
        "khi nào được coi": "khi_nao_la_vo_chong_hop_phap",
        "có cần đăng ký kết hôn": "co_can_dang_ky",
        "có cần đăng ký": "co_can_dang_ky",
    },
    "hoan_canh_ca_nhan": {
        "án treo": "dang_chap_hanh_an_treo",
        "chưa xóa án tích": "chua_duoc_xoa_an_tich",
        "còn án tích": "chua_duoc_xoa_an_tich",
        "bại liệt": "bai_liet_hoac_khuyet_tat_the_chat",
        "liệt nửa người": "bai_liet_hoac_khuyet_tat_the_chat",
        "khuyết tật thể chất": "bai_liet_hoac_khuyet_tat_the_chat",
        "mất năng lực hành vi dân sự": "bi_mat_nang_luc_hanh_vi_dan_su",
    },
    "tinh_trang_nang_luc_hanh_vi": {
        "mất năng lực hành vi dân sự": "bi_mat",
        "vẫn nhận thức làm chủ": "khong_bi_mat",
    },
    "khia_canh_anh_huong": {
        "có được kết hôn": "co_duoc_ket_hon",
        "có được không": "co_duoc_ket_hon",
        "có bị cấm": "co_tu_dong_bi_cam",
        "cần kiểm tra gì": "can_kiem_tra_dieu_kien_nao",
    },
    "yeu_to_xa_hoi": {
        "khác tín ngưỡng": "khac_tin_nguong_gia_dinh_phan_doi",
        "khác đạo": "khac_tin_nguong_gia_dinh_phan_doi",
        "ông bà không đồng ý": "khac_tin_nguong_gia_dinh_phan_doi",
        "bố mẹ không đồng ý": "khac_tin_nguong_gia_dinh_phan_doi",
        "chưa cắt khẩu": "ho_khau_sau_ly_hon",
        "hộ khẩu ở nhà chồng cũ": "ho_khau_sau_ly_hon",
        "giáo viên với học sinh": "quan_he_giao_vien_hoc_sinh",
        "thầy cô với học sinh": "quan_he_giao_vien_hoc_sinh",
        "xung khắc tuổi": "xung_khac_tuoi",
        "khắc tuổi": "xung_khac_tuoi",
        "không hợp tuổi": "xung_khac_tuoi",
    },
    "tinh_trang_hon_nhan_hien_tai": {
        "đã ly hôn": "da_ly_hon",
        "chưa ly hôn": "dang_co_vo_chong",
        "đang có chồng": "dang_co_vo_chong",
        "độc thân": "chua_co_vo_chong",
    },
    "khia_canh_yeu_to_xa_hoi": {
        "có lấy nhau được không": "co_duoc_ket_hon",
        "có phải trở ngại không": "co_phai_tro_ngai",
        "điều kiện cần kiểm tra": "dieu_kien_can_kiem_tra",
    },
    "khia_canh_tong_quat": {
        "điều kiện kết hôn là gì": "giai_thich_khai_niem",
        "cần đáp ứng điều kiện nào": "liet_ke_dieu_kien",
        "cần đáp ứng những gì": "liet_ke_dieu_kien",
        "đã đủ hết chưa": "kiem_tra_day_du",
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
