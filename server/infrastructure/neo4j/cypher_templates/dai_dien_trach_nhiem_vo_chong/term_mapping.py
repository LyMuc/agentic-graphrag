"""Ánh xạ thuật ngữ thông thường → param chuẩn cho topic dai_dien_trach_nhiem_vo_chong."""
from __future__ import annotations

import re
from typing import Any, Optional

COMMON_TO_LEGAL_TERMS: dict[str, dict[str, Any]] = {
    "pham_vi_giao_dich": {
        "căn cứ xác lập đại diện": "tat_ca",
        "đại diện theo luật nào": "tat_ca",
        "xác lập giao dịch": "xac_lap",
        "thực hiện giao dịch": "thuc_hien",
        "chấm dứt giao dịch": "cham_dut",
    },
    "co_uy_quyen_hoac_dong_y": {
        "ủy quyền cho nhau": "co",
        "ủy quyền cho vợ": "co",
        "ủy quyền cho chồng": "co",
        "một mình ký": "khong",
        "tự ký": "khong",
        "vợ không đồng ý": "khong",
        "chồng không đồng ý": "khong",
    },
    "doi_tuong_giao_dich": {
        "phải có sự đồng ý của cả hai": "giao_dich_can_dong_y_ca_hai",
        "cả hai cùng đồng ý": "giao_dich_can_dong_y_ca_hai",
    },
    "tinh_trang_nang_luc": {
        "mất năng lực hành vi dân sự": "mat_nang_luc",
        "hạn chế năng lực hành vi dân sự": "han_che_nang_luc",
    },
    "can_cu_dai_dien": {
        "đủ điều kiện làm người giám hộ": "du_dieu_kien_giam_ho",
        "tòa án chỉ định làm đại diện": "toa_an_chi_dinh",
    },
    "boi_canh": {
        "phải tự mình thực hiện": "quyen_nghia_vu_phai_tu_minh",
        "mọi giao dịch không": "quyen_nghia_vu_phai_tu_minh",
        "đại diện khi ly hôn": "ly_hon",
        "ai đại diện trong vụ ly hôn": "ly_hon",
    },
    "boi_canh_kinh_doanh": {
        "kinh doanh chung": "kinh_doanh_chung",
        "làm ăn chung": "kinh_doanh_chung",
        "ký hợp đồng mua bán hàng hóa": "mot_ben_ky_giao_dich",
        "thỏa thuận một người làm đại diện": "co_thoa_thuan_dai_dien",
    },
    "co_thoa_thuan_khac": {
        "thỏa thuận một người làm đại diện": "co",
    },
    "khia_canh": {
        "đưa tài sản chung vào kinh doanh": "quy_dinh_ap_dung",
        "góp tài sản chung làm ăn": "quy_dinh_ap_dung",
    },
    "hinh_thuc_thoa_thuan": {
        "thỏa thuận bằng lời nói": "loi_noi",
        "nói miệng": "loi_noi",
        "thỏa thuận bằng văn bản": "van_ban",
    },
    "loai_giay_chung_nhan": {
        "giấy chứng nhận quyền sử dụng đất": "gcn_quyen_su_dung",
        "sổ đỏ": "gcn_quyen_su_dung",
        "giấy chứng nhận quyền sở hữu": "gcn_quyen_so_huu",
        "sổ hồng": "gcn_quyen_so_huu",
    },
    "nguoi_dung_ten": {
        "chỉ đứng tên vợ": "vo",
        "chỉ đứng tên chồng": "chong",
        "chỉ ghi tên một người": "mot_ben",
        "chỉ ghi tên một bên": "mot_ben",
    },
    "hanh_vi_giao_dich": {
        "tự bán nhà": "ban_chuyen_nhuong",
        "một mình chuyển nhượng": "ban_chuyen_nhuong",
    },
    "trong_tam_hau_qua": {
        "vô hiệu": "vo_hieu",
        "có hiệu lực không": "vo_hieu",
        "mọi trường hợp": "co_ngoai_le",
        "luôn vô hiệu": "co_ngoai_le",
        "có ngoại lệ không": "co_ngoai_le",
    },
    "tinh_trang_nguoi_thu_ba": {
        "người mua ngay tình": "ngay_tinh",
        "người thứ ba ngay tình": "ngay_tinh",
    },
    "nhom_can_cu": {
        "trách nhiệm liên đới": "tong_quat",
        "cùng chịu trách nhiệm": "tong_quat",
        "giao dịch do một bên thực hiện": "giao_dich_dai_dien",
        "nợ chung": "nghia_vu_chung",
        "nghĩa vụ chung": "nghia_vu_chung",
        "tài sản chung trả nợ riêng": "doi_chieu_chung_rieng",
        "nợ chung hay riêng": "doi_chieu_chung_rieng",
        "vợ có phải trả nợ chồng": "doi_chieu_chung_rieng",
    },
    "muc_dich_no": {
        "nợ riêng": "ca_nhan",
        "không dùng cho gia đình": "ca_nhan",
        "vay cá nhân": "ca_nhan",
        "nhu cầu gia đình": "nhu_cau_gia_dinh",
        "tiền sinh hoạt": "nhu_cau_gia_dinh",
        "nhu cầu thiết yếu": "nhu_cau_gia_dinh",
        "vay làm ăn chung": "kinh_doanh_chung",
    },
    "thoi_diem_no": {
        "trong thời kỳ hôn nhân": "trong_hon_nhan",
    },
    "tinh_trang_hon_nhan": {
        "đang ly hôn": "dang_ly_hon",
        "khi ly hôn": "dang_ly_hon",
        "đã ly hôn": "da_ly_hon",
        "sau ly hôn": "da_ly_hon",
    },
    "nguoi_thu_ba": {
        "ngân hàng": "ngan_hang",
        "chủ nợ": "chu_no",
        "người cho vay": "chu_no",
    },
    "tai_san_thanh_toan": {
        "lấy tài sản chung trả nợ": "tai_san_chung",
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
