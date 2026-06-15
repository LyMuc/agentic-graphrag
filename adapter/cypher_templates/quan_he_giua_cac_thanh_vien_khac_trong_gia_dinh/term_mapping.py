"""Ánh xạ thuật ngữ thông thường → param chuẩn cho topic quan_he_giua_cac_thanh_vien_khac_trong_gia_dinh."""
from __future__ import annotations

import re
from typing import Any, Optional

COMMON_TO_LEGAL_TERMS: dict[str, dict[str, Any]] = {
    "khia_canh_chung": {
        "pháp luật bảo vệ": "bao_ve_quyen_loi",
        "nhà nước có chính sách gì": "chinh_sach_nha_nuoc",
        "nhà nước khuyến khích": "chinh_sach_nha_nuoc",
    },
    "nhom_noi_dung": {
        "quyền lợi nhân thân": "nhan_than_va_tai_san",
        "quyền lợi tài sản": "nhan_than_va_tai_san",
        "giữ gìn truyền thống gia đình": "giu_gin_truyen_thong_gia_dinh",
    },
    "loai_nghia_vu_song_chung": {
        "công việc gia đình": "tham_gia_cong_viec_gia_dinh",
        "lao động tạo thu nhập": "lao_dong_tao_thu_nhap",
        "đóng góp công sức": "dong_gop_cong_suc",
        "tiền ăn ở": "dong_gop_tien",
        "đóng góp tiền": "dong_gop_tien",
        "tài sản khác": "dong_gop_tai_san_khac",
    },
    "khia_canh_danh_gia": {
        "sống chung": "pham_vi_nghia_vu",
        "theo khả năng thực tế": "muc_dong_gop",
    },
    "quan_he_tinh_huong": {
        "dì ruột sống chung": "di_va_chau",
    },
    "chieu_ong_ba_chau": {
        "ông bà nội": "ong_ba_doi_voi_chau",
        "ông bà ngoại": "ong_ba_doi_voi_chau",
    },
    "chieu_nuoi_duong_ong_ba_chau": {
        "ông bà nội": "ong_ba_nuoi_chau",
        "ông bà ngoại": "ong_ba_nuoi_chau",
        "cháu nuôi ông bà": "chau_thanh_nien_nuoi_ong_ba",
    },
    "noi_dung_ong_ba_chau": {
        "trông nom, chăm sóc, giáo dục": "trong_nom_cham_soc_giao_duc",
        "sống mẫu mực, nêu gương": "song_mau_muc_neu_guong",
        "kính trọng, chăm sóc, phụng dưỡng": "kinh_trong_cham_soc_phung_duong",
    },
    "tinh_trang_chau": {
        "cháu chưa thành niên": "chua_thanh_nien",
        "cháu 16 tuổi": "chua_thanh_nien",
        "mất năng lực hành vi dân sự": "thanh_nien_mat_nang_luc_hanh_vi_dan_su",
        "không có khả năng lao động và không có tài sản": "thanh_nien_khong_kha_nang_lao_dong_va_khong_co_tai_san",
    },
    "nguoi_nuoi_duong_theo_dieu_105": {
        "không có anh chị em nuôi dưỡng": "khong_co",
        "anh chị em không có điều kiện nuôi": "co_nhung_khong_co_dieu_kien",
    },
    "tinh_trang_con_cua_ong_ba": {
        "ông bà không có con": "khong_co_con",
    },
    "chau_da_thanh_nien": {
        "cháu đã thành niên": "co",
    },
    "tinh_trang_cha_me": {
        "không còn cha mẹ": "khong_con",
        "mồ côi cha mẹ": "khong_con",
        "cha mẹ bị tù, không còn ai trông nom": "khong_co_dieu_kien",
        "cha mẹ già yếu, bệnh tật không còn sức chăm sóc": "khong_co_dieu_kien",
    },
    "noi_dung_anh_chi_em": {
        "anh chị em thương yêu, chăm sóc, giúp đỡ nhau": "tong_hop",
    },
    "cung_song": {
        "hai anh em cùng sống": "co",
    },
    "doi_tuong_ho_hang": {
        "cô ruột": "co",
        "dì ruột": "di",
        "chú ruột": "chu",
        "cậu ruột": "cau",
        "bác ruột": "bac",
    },
    "chieu_ho_hang_chau": {
        "cháu chăm sóc, giúp đỡ chú": "chau_doi_voi_ho_hang",
        "cháu chăm sóc, giúp đỡ cậu": "chau_doi_voi_ho_hang",
        "cháu chăm sóc, giúp đỡ bác": "chau_doi_voi_ho_hang",
    },
    "chieu_nuoi_duong_ho_hang": {
        "cô nuôi cháu": "ho_hang_nuoi_chau_ruot",
        "dì nuôi cháu": "ho_hang_nuoi_chau_ruot",
        "chú nuôi cháu": "ho_hang_nuoi_chau_ruot",
        "cô/dì/chú/cậu/bác nuôi cháu": "ho_hang_nuoi_chau_ruot",
        "cháu nuôi cậu": "chau_ruot_nuoi_ho_hang",
        "cháu nuôi chú": "chau_ruot_nuoi_ho_hang",
        "cháu nuôi bác": "chau_ruot_nuoi_ho_hang",
    },
    "noi_dung_ho_hang_chau": {
        "thương yêu, chăm sóc, giúp đỡ nhau": "tong_hop",
    },
    "con_cha_me_cua_nguoi_can_nuoi_duong": {
        "không còn cha, mẹ": "khong",
    },
    "con_con_cua_nguoi_can_nuoi_duong": {
        "không còn con": "khong",
    },
    "tinh_trang_nguoi_thuoc_dieu_104_105": {
        "ông bà đã mất, anh chị em không có điều kiện": "khong_con_hoac_khong_co_dieu_kien",
        "không còn ông bà, anh chị em": "khong_con",
        "ông bà, anh chị em không có điều kiện": "con_nhung_khong_co_dieu_kien",
        "chỉ nêu không có anh chị em": "chi_biet_mot_phan",
    },
    "khia_canh_nuoi_duong_ho_hang": {
        "khác gì so với ông bà và cháu": "so_sanh_voi_ong_ba_chau",
    },
    "con_cha_me_cua_chau": {
        "cha mẹ cháu còn": "co",
    },
    "khia_canh_ho_hang": {
        "khi cha mẹ cháu còn": "phan_biet_voi_nuoi_duong",
    },
}


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().strip())


def resolve_term(field: str, raw_text: Optional[str]) -> Optional[Any]:
    if not raw_text or field not in COMMON_TO_LEGAL_TERMS:
        return None
    norm = _normalize(raw_text)
    if field in ("con_cha_me_cua_nguoi_can_nuoi_duong", "con_con_cua_nguoi_can_nuoi_duong"):
        if re.search(r"không còn vợ|không còn chồng|không còn vợ/chồng", norm):
            return None
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
