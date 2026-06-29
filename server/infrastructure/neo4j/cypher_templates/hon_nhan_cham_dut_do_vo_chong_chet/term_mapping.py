"""Ánh xạ thuật ngữ thông thường → param chuẩn cho topic hon_nhan_cham_dut_do_vo_chong_chet."""
from __future__ import annotations

import re
from typing import Any, Optional

COMMON_TO_LEGAL_TERMS: dict[str, dict[str, Any]] = {
    "can_cu_cham_dut": {
        "vợ chết": "chet_thuc_te",
        "chồng chết": "chet_thuc_te",
        "mất do tai nạn": "chet_thuc_te",
        "qua đời": "chet_thuc_te",
        "không may bị chết": "chet_thuc_te",
        "tòa tuyên bố đã chết": "bi_tuyen_bo_da_chet",
        "bị tuyên là đã chết": "bi_tuyen_bo_da_chet",
        "tuyên bố đã chết": "bi_tuyen_bo_da_chet",
        "biệt tích": "biet_tich_chua_co_tuyen_bo",
        "mất tích": "biet_tich_chua_co_tuyen_bo",
        "mất liên lạc": "biet_tich_chua_co_tuyen_bo",
        "không có tin tức": "biet_tich_chua_co_tuyen_bo",
    },
    "su_kien": {
        "vợ chết": "chet_thuc_te",
        "chồng chết": "chet_thuc_te",
        "mất do tai nạn": "chet_thuc_te",
        "qua đời": "chet_thuc_te",
        "tòa tuyên bố đã chết": "bi_tuyen_bo_da_chet",
        "bị tuyên là đã chết": "bi_tuyen_bo_da_chet",
        "một bên chết": "mot_ben_chet_hoac_bi_tuyen_bo_da_chet",
        "chết hoặc bị tòa": "mot_ben_chet_hoac_bi_tuyen_bo_da_chet",
    },
    "loai_quyet_dinh_truoc_khi_tro_ve": {
        "tòa tuyên bố đã chết": "tuyen_bo_da_chet",
        "bị tuyên bố đã chết": "tuyen_bo_da_chet",
        "tòa tuyên bố mất tích": "tuyen_bo_mat_tich",
        "tuyên bố mất tích": "tuyen_bo_mat_tich",
        "bị tuyên bố mất tích": "tuyen_bo_mat_tich",
    },
    "khia_canh_thoi_diem": {
        "khi nào chấm dứt": "thoi_diem_cham_dut",
        "thời điểm nào": "thoi_diem_cham_dut",
        "thời điểm chấm dứt": "thoi_diem_cham_dut",
        "có chấm dứt không": "co_cham_dut_hay_khong",
        "có chấm dứt hay không": "co_cham_dut_hay_khong",
        "lấy chồng mới": "co_duoc_ket_hon_voi_nguoi_khac",
        "lấy vợ mới": "co_duoc_ket_hon_voi_nguoi_khac",
        "tái hôn": "co_duoc_ket_hon_voi_nguoi_khac",
        "kết hôn người khác": "co_duoc_ket_hon_voi_nguoi_khac",
        "biệt tích bao nhiêu năm": "dieu_kien_tuyen_bo_da_chet",
        "bao nhiêu năm": "dieu_kien_tuyen_bo_da_chet",
    },
    "chu_the_xay_ra_su_kien": {
        "chồng": "chong",
        "người chồng": "chong",
        "vợ": "vo",
        "người vợ": "vo",
    },
    "khia_canh_tai_san_66": {
        "bên còn sống quản lý": "quan_ly_tai_san_chung",
        "trông coi tài sản chung": "quan_ly_tai_san_chung",
        "quản lý tài sản chung": "quan_ly_tai_san_chung",
        "ai quản lý di sản": "nguoi_quan_ly_di_san",
        "di chúc chỉ định người quản lý": "nguoi_quan_ly_di_san",
        "chia tài sản chung": "chia_tai_san_va_di_san",
        "chia di sản": "chia_tai_san_va_di_san",
        "giải quyết tài sản chung": "chia_tai_san_va_di_san",
        "ảnh hưởng nghiêm trọng đời sống": "han_che_phan_chia_di_san",
        "làm gia đình khó khăn": "han_che_phan_chia_di_san",
        "hạn chế phân chia": "han_che_phan_chia_di_san",
        "tài sản kinh doanh": "tai_san_trong_kinh_doanh",
        "đưa vào kinh doanh": "tai_san_trong_kinh_doanh",
    },
    "khia_canh_tai_san_67": {
        "khôi phục quan hệ tài sản": "khoi_phuc_quan_he_tai_san",
        "tài sản trong thời gian bị tuyên bố": "tai_san_trong_thoi_gian_bi_tuyen_bo_da_chet",
        "tài sản trước đó chưa chia": "tai_san_truoc_tuyen_bo_chua_chia",
        "tài sản chung cũ": "tai_san_truoc_tuyen_bo_chua_chia",
        "có được chia lại": "co_duoc_chia_lai_hay_khong",
        "chia lại tài sản": "co_duoc_chia_lai_hay_khong",
    },
    "co_yeu_cau_chia_di_san": {
        "yêu cầu chia di sản": "co",
        "đòi chia di sản": "co",
    },
    "co_thoa_thuan_che_do_tai_san": {
        "thỏa thuận tài sản": "co",
        "thỏa thuận chế độ tài sản": "co",
        "có thỏa thuận": "co",
    },
    "anh_huong_nghiem_trong_den_doi_song": {
        "ảnh hưởng nghiêm trọng": "co",
        "khó khăn đời sống": "co",
    },
    "quyet_dinh_huy_bo_tuyen_bo_da_chet": {
        "tòa hủy bỏ tuyên bố đã chết": "da_co",
        "hủy bỏ tuyên bố đã chết": "da_co",
    },
    "tinh_trang_cua_ben_con_lai": {
        "chưa lấy ai": "chua_ket_hon_nguoi_khac",
        "chưa kết hôn người khác": "chua_ket_hon_nguoi_khac",
        "đã ly hôn": "da_co_quyet_dinh_ly_hon",
        "quyết định cho ly hôn": "da_co_quyet_dinh_ly_hon",
        "đã lấy người khác": "da_ket_hon_nguoi_khac",
        "đã tái hôn": "da_ket_hon_nguoi_khac",
        "đã kết hôn người khác": "da_ket_hon_nguoi_khac",
    },
    "tinh_trang_khoi_phuc_hon_nhan": {
        "hôn nhân được khôi phục": "duoc_khoi_phuc",
        "được khôi phục hôn nhân": "duoc_khoi_phuc",
        "hôn nhân không được khôi phục": "khong_duoc_khoi_phuc",
        "không được khôi phục": "khong_duoc_khoi_phuc",
    },
    "khia_canh_khoi_phuc": {
        "có được khôi phục hôn nhân": "co_duoc_khoi_phuc_hay_khong",
        "hôn nhân cũ còn không": "co_duoc_khoi_phuc_hay_khong",
        "điều kiện khôi phục": "dieu_kien_khoi_phuc",
        "quyết định ly hôn còn hiệu lực": "hieu_luc_quyet_dinh_ly_hon",
        "hôn nhân sau có hiệu lực": "hieu_luc_hon_nhan_sau",
    },
}


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().strip())


def resolve_term(
    field: str,
    raw_text: Optional[str],
    valid_values: Optional[frozenset[str]] = None,
) -> Optional[Any]:
    if not raw_text or field not in COMMON_TO_LEGAL_TERMS:
        return None
    norm = _normalize(raw_text)
    mapping = COMMON_TO_LEGAL_TERMS[field]
    for pattern in sorted(mapping.keys(), key=len, reverse=True):
        if pattern.lower() in norm:
            value = mapping[pattern]
            if valid_values is not None and value not in valid_values:
                continue
            return value
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
