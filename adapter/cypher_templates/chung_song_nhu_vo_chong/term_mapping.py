"""Ánh xạ thuật ngữ thông thường → param chuẩn cho topic chung_song_nhu_vo_chong."""
from __future__ import annotations

import re
from typing import Any, Optional

COMMON_TO_LEGAL_TERMS: dict[str, dict[str, Any]] = {
    "tinh_trang_hon_nhan_cac_ben": {
        "cả hai độc thân": "ca_hai_chua_co_vo_chong",
        "chưa ai có vợ chồng": "ca_hai_chua_co_vo_chong",
        "đang có vợ": "mot_ben_dang_co_vo_chong",
        "đang có chồng": "mot_ben_dang_co_vo_chong",
        "đã có gia đình": "mot_ben_dang_co_vo_chong",
        "chưa ly hôn": "mot_ben_dang_co_vo_chong",
        "bạn trai": "khong_ro",
        "bạn gái": "khong_ro",
    },
    "khia_canh_hop_phap": {
        "có vi phạm không": "co_vi_pham_hay_khong",
        "có bị cấm không": "co_vi_pham_hay_khong",
        "trường hợp nào bị cấm": "truong_hop_bi_cam",
        "sống thử có phải luôn vi phạm": "phan_biet_bi_cam_va_khong_dang_ky",
    },
    "tinh_trang_dang_ky": {
        "không đăng ký kết hôn": "chua_dang_ky",
        "không có giấy kết hôn": "chua_dang_ky",
        "chưa đăng ký": "chua_dang_ky",
        "sắp cưới": "du_dinh_dang_ky",
        "định đăng ký": "du_dinh_dang_ky",
    },
    "khia_canh_thoi_diem": {
        "bao lâu thì phải cưới": "co_bat_buoc_sau_bao_lau",
        "bao lâu thì phải kết hôn": "co_bat_buoc_sau_bao_lau",
        "hôn nhân tính từ khi nào": "thoi_diem_xac_lap_hon_nhan",
        "tính là vợ chồng từ khi nào": "thoi_diem_xac_lap_hon_nhan",
        "có tính từ lúc dọn về": "hieu_luc_thoi_gian_chung_song_truoc_do",
    },
    "khia_canh_con": {
        "ai nuôi con": "nuoi_con",
        "quyền nuôi con": "nuoi_con",
        "chăm sóc con": "cham_soc_giao_duc",
        "trông nom con": "cham_soc_giao_duc",
        "giáo dục con": "cham_soc_giao_duc",
        "cấp dưỡng": "cap_duong",
        "tiền nuôi con": "cap_duong",
        "quyền của con": "quyen",
        "nghĩa vụ cha mẹ": "nghia_vu",
    },
    "co_thoa_thuan": {
        "đã thống nhất": "co",
        "có giấy thỏa thuận": "co",
        "không thỏa thuận được": "khong",
        "không có thỏa thuận": "khong",
    },
    "khia_canh_tai_san": {
        "chia tài sản": "chia_tai_san",
        "phân chia tài sản": "chia_tai_san",
        "tài sản lúc sống thử": "nguyen_tac_giai_quyet",
        "giải quyết theo luật nào": "nguyen_tac_giai_quyet",
        "bảo vệ phụ nữ và con": "bao_ve_phu_nu_va_con",
        "công sức nội trợ": "cong_suc_noi_tro",
        "ở nhà chăm con": "cong_suc_noi_tro",
    },
    "loai_quan_he": {
        "nợ": "nghia_vu",
        "khoản vay": "nghia_vu",
        "ai phải trả": "nghia_vu",
        "hợp đồng": "hop_dong",
        "giao dịch đã ký": "hop_dong",
    },
    "khia_canh_hau_qua": {
        "hậu quả": "tong_quat",
        "giải quyết thế nào": "tong_quat",
        "có được coi là vợ chồng": "quan_he_vo_chong",
        "quan hệ vợ chồng": "quan_he_vo_chong",
        "con": "con",
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
