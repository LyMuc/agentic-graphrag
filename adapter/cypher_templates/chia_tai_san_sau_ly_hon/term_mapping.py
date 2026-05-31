"""Ánh xạ thuật ngữ thông thường → param chuẩn cho topic chia_tai_san_sau_ly_hon."""
from __future__ import annotations

import re
from typing import Any, Optional

COMMON_TO_LEGAL_TERMS: dict[str, dict[str, Any]] = {
    "khia_canh": {
        "chia đều": "chia_doi",
        "chia đôi": "chia_doi",
        "50/50": "chia_doi",
        "nguyên tắc": "tong_quat",
        "giải quyết tài sản khi ly hôn": "tong_quat",
        "yếu tố nào": "yeu_to_chia",
        "tính đến yếu tố": "yeu_to_chia",
        "nội trợ": "cong_suc_noi_tro",
        "chăm con": "cong_suc_noi_tro",
        "ở nhà chăm con": "cong_suc_noi_tro",
        "lỗi": "loi_vi_pham",
        "ngoại tình": "loi_vi_pham",
        "gian dối": "loi_vi_pham",
        "vi phạm nghĩa vụ": "loi_vi_pham",
        "hiện vật": "chia_hien_vat_gia_tri",
        "chênh lệch": "chia_hien_vat_gia_tri",
        "sáp nhập": "tai_san_rieng_nhap_chung",
        "trộn lẫn": "tai_san_rieng_nhap_chung",
        "tài sản riêng nhập chung": "tai_san_rieng_nhap_chung",
        "vợ con": "bao_ve_vo_con",
        "con chưa thành niên": "bao_ve_vo_con",
    },
    "loai_tai_san": {
        "nhà trả góp": "nha_mua_tra_gop",
        "căn nhà mua trả góp": "nha_mua_tra_gop",
        "mua trả góp": "nha_mua_tra_gop",
        "nhà đất": "bat_dong_san",
        "căn nhà": "bat_dong_san",
        "bất động sản": "bat_dong_san",
        "nhà": "bat_dong_san",
        "quyền sử dụng đất": "quyen_su_dung_dat",
        "sổ đỏ": "quyen_su_dung_dat",
        "đất": "quyen_su_dung_dat",
        "trợ cấp": "tai_khoan_tiet_kiem_tro_cap",
        "thương binh": "tai_khoan_tiet_kiem_tro_cap",
        "sổ tiết kiệm": "tai_khoan_tiet_kiem_tro_cap",
        "tài khoản tiết kiệm": "tai_khoan_tiet_kiem_tro_cap",
        "cho ngày cưới": "tai_san_duoc_tang_cho_ngay_cuoi",
        "quà cưới": "tai_san_duoc_tang_cho_ngay_cuoi",
        "ô tô": "dong_san_phai_dang_ky",
        "xe hơi": "dong_san_phai_dang_ky",
        "xe máy": "dong_san_phai_dang_ky",
    },
    "nguon_goc": {
        "trả góp": "tra_gop",
        "bố mẹ cho": "tang_cho",
        "được cho": "tang_cho",
        "cho riêng": "tang_cho_rieng",
        "tặng cho riêng": "tang_cho_rieng",
        "chỉ mình tôi": "tang_cho_rieng",
        "trong thời kỳ hôn nhân": "trong_hon_nhan",
        "đứng tên chồng": "dung_ten_mot_ben",
        "đứng tên vợ": "dung_ten_mot_ben",
        "chỉ đứng tên": "dung_ten_mot_ben",
        "ly thân": "ly_than",
        "đã trả nửa": "da_chia_sau_ly_hon",
        "đã thanh toán": "da_chia_sau_ly_hon",
        "đã chia xong": "da_chia_sau_ly_hon",
    },
    "loai_nghia_vu": {
        "nợ chung": "no_chung",
        "vay làm ăn": "vay_kinh_doanh",
        "vay kinh doanh": "vay_kinh_doanh",
        "vay riêng": "vay_ca_nhan",
        "không sử dụng": "vay_ca_nhan",
        "cá nhân": "vay_ca_nhan",
        "tranh chấp": "tranh_chap",
        "người thứ ba": "quyen_nghia_vu_nguoi_thu_ba",
    },
    "nguoi_thu_ba": {
        "ngân hàng": "ngan_hang",
        "chủ nợ": "chu_no",
        "người cho vay": "chu_no",
    },
    "muc_dich_no": {
        "làm ăn": "kinh_doanh",
        "kinh doanh": "kinh_doanh",
        "sinh hoạt gia đình": "nhu_cau_gia_dinh",
        "nhu cầu gia đình": "nhu_cau_gia_dinh",
        "không sử dụng": "ca_nhan",
        "cá nhân": "ca_nhan",
    },
    "thoi_diem_no": {
        "trong thời kỳ hôn nhân": "trong_hon_nhan",
        "sau ly hôn": "sau_ly_hon",
    },
    "loai_dat": {
        "đất nông nghiệp hằng năm": "dat_nong_nghiep_hang_nam_nuoi_trong_thuy_san",
        "nuôi trồng thủy sản": "dat_nong_nghiep_hang_nam_nuoi_trong_thuy_san",
        "đất ở": "dat_cay_lau_nam_dat_lam_nghiep_dat_o",
        "đất lâm nghiệp": "dat_cay_lau_nam_dat_lam_nghiep_dat_o",
        "đất trồng cây lâu năm": "dat_cay_lau_nam_dat_lam_nghiep_dat_o",
    },
    "loai_truong_hop": {
        "sống chung với gia đình": "song_chung_voi_gia_dinh",
        "khối tài sản chung của gia đình": "song_chung_voi_gia_dinh",
        "ở lại nhà riêng": "luu_cu_nha_rieng",
        "lưu cư": "luu_cu_nha_rieng",
        "khó khăn chỗ ở": "luu_cu_nha_rieng",
    },
    "hanh_vi_context": {
        "mua đất giấu vợ": "mua_dat_giau_vo",
        "đứng tên": "dung_ten_mot_ben",
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


__all__ = ["COMMON_TO_LEGAL_TERMS", "resolve_term"]
