"""Ánh xạ thuật ngữ thông thường → param chuẩn cho topic dang_ky_ket_hon."""
from __future__ import annotations

import re
from typing import Any, Optional

COMMON_TO_LEGAL_TERMS: dict[str, dict[str, Any]] = {
    "khia_canh_tham_quyen": {
        "ở đâu": "dia_diem",
        "đăng ký chỗ nào": "dia_diem",
        "nơi nào": "dia_diem",
        "cơ quan nào": "co_quan",
        "cấp xã hay cấp huyện": "cap_co_quan",
        "cấp nào": "cap_co_quan",
    },
    "ben_co_noi_cu_tru": {
        "ở nhà vợ": "ben_nu",
        "quê vợ": "ben_nu",
        "bên nhà gái": "ben_nu",
        "ở nhà chồng": "ben_nam",
        "quê chồng": "ben_nam",
        "bên nhà trai": "ben_nam",
        "một trong hai bên": "mot_trong_hai",
    },
    "loai_noi_cu_tru": {
        "hộ khẩu": "thuong_tru",
        "thường trú": "thuong_tru",
        "tạm trú": "tam_tru",
        "kt3": "tam_tru",
        "chỗ ở tạm": "tam_tru",
        "nơi đang ở hiện tại": "noi_o_hien_tai",
    },
    "cap_dang_ky": {
        "phường": "cap_xa",
        "xã": "cap_xa",
        "thị trấn": "cap_xa",
        "quận": "cap_huyen",
        "huyện": "cap_huyen",
        "ubnd huyện": "cap_huyen",
        "xã biên giới": "xa_bien_gioi",
        "người nước láng giềng": "xa_bien_gioi",
    },
    "boi_canh_chu_the": {
        "người nước ngoài": "cong_dan_vn_voi_nguoi_nuoc_ngoai",
        "lấy chồng tây": "cong_dan_vn_voi_nguoi_nuoc_ngoai",
        "lấy vợ nước ngoài": "cong_dan_vn_voi_nguoi_nuoc_ngoai",
        "việt kiều": "cong_dan_vn_dinh_cu_o_nuoc_ngoai",
        "định cư ở nước ngoài": "cong_dan_vn_dinh_cu_o_nuoc_ngoai",
        "hai người nước ngoài ở việt nam": "nguoi_nuoc_ngoai_cu_tru_vn",
        "hai công dân việt nam": "trong_nuoc",
    },
    "khia_canh_dieu_kien_gia_tri": {
        "cần điều kiện gì": "dieu_kien_ket_hon",
        "có đủ điều kiện không": "dieu_kien_ket_hon",
        "cưới mà không đăng ký": "gia_tri_khi_khong_dang_ky",
        "không có giấy kết hôn": "gia_tri_khi_khong_dang_ky",
        "có được công nhận là vợ chồng": "gia_tri_khi_khong_dang_ky",
        "trước đám cưới bao lâu": "thoi_diem_so_voi_le_cuoi",
        "trước lễ cưới mấy ngày": "thoi_diem_so_voi_le_cuoi",
        "đăng ký sai nơi": "xu_ly_sai_tham_quyen",
        "sai thẩm quyền": "xu_ly_sai_tham_quyen",
    },
    "tinh_trang_dang_ky": {
        "chỉ cưới": "chua_dang_ky",
        "chung sống, chưa đăng ký": "chua_dang_ky",
        "đăng ký nhầm": "sai_tham_quyen",
        "sai cơ quan": "sai_tham_quyen",
    },
    "tinh_trang_truoc_do": {
        "vợ chồng cũ quay lại": "da_ly_hon",
        "tái hôn với nhau sau ly hôn": "da_ly_hon",
        "đã ly hôn": "da_ly_hon",
        "có bản án ly hôn": "da_ly_hon",
    },
    "khia_canh_ket_hon_lai": {
        "kết hôn lại sau ly hôn có phải đăng ký": "co_phai_dang_ky",
        "xác lập lại quan hệ vợ chồng": "xac_lap_lai_quan_he",
        "có được kết hôn lại không": "co_duoc_ket_hon_lai",
    },
    "khia_canh_thu_tuc": {
        "thủ tục": "trinh_tu_xu_ly",
        "quy trình": "trinh_tu_xu_ly",
        "trình tự thế nào": "trinh_tu_xu_ly",
        "hồ sơ cần nộp": "ho_so_nop",
        "giấy tờ cần nộp": "ho_so_nop",
        "nhờ người khác làm": "su_co_mat_va_uy_quyen",
        "đăng ký giùm": "su_co_mat_va_uy_quyen",
        "ủy quyền": "su_co_mat_va_uy_quyen",
        "phải cùng đi": "su_co_mat_va_uy_quyen",
        "phải có mặt cả hai": "su_co_mat_va_uy_quyen",
    },
    "khia_canh_thoi_han": {
        "xác minh điều kiện": "xac_minh_dieu_kien",
        "giải quyết hồ sơ bao lâu": "giai_quyet_ho_so",
        "đăng ký lại mất bao lâu": "dang_ky_lai",
    },
    "khia_canh_tu_choi": {
        "bị từ chối": "truong_hop_bi_tu_choi",
        "không được chấp nhận": "truong_hop_bi_tu_choi",
        "trả lời bằng văn bản": "thong_bao_ly_do",
        "nêu rõ lý do": "thong_bao_ly_do",
    },
    "ly_do_tu_choi": {
        "thuộc điều cấm": "vi_pham_dieu_cam",
        "không đủ tuổi": "khong_du_dieu_kien",
        "không tự nguyện": "khong_du_dieu_kien",
        "mất năng lực": "khong_du_dieu_kien",
    },
    "khia_canh_noi_dung": {
        "giấy chứng nhận có thông tin gì": "tat_ca",
        "nội dung gì": "tat_ca",
        "họ tên": "thong_tin_nhan_than",
        "ngày sinh": "thong_tin_nhan_than",
        "quốc tịch": "thong_tin_nhan_than",
        "nơi cư trú": "thong_tin_nhan_than",
        "ngày đăng ký": "ngay_dang_ky",
        "chữ ký": "chu_ky_xac_nhan",
        "điểm chỉ": "chu_ky_xac_nhan",
        "xác nhận": "chu_ky_xac_nhan",
    },
    "khia_canh_cap_trao": {
        "lễ trao": "to_chuc_trao",
        "tổ chức trao": "to_chuc_trao",
        "nhận giấy": "to_chuc_trao",
        "mấy bản chính": "so_ban_chinh",
        "bao nhiêu bản": "so_ban_chinh",
    },
    "khia_canh_dang_ky_lai": {
        "cấp lại giấy": "dieu_kien",
        "đăng ký lại giấy kết hôn": "dieu_kien",
        "khi nào được cấp lại": "dieu_kien",
        "hồ sơ đăng ký lại": "ho_so",
        "đăng ký lại mất bao lâu": "thu_tuc_thoi_han",
        "hôn nhân tính từ ngày đăng ký cũ": "hieu_luc_quan_he",
    },
    "tinh_trang_luu_tru": {
        "mất cả sổ và bản chính": "so_va_ban_chinh_deu_mat",
        "chỉ mất giấy kết hôn": "chi_mat_ban_chinh",
        "chỉ mất sổ hộ tịch": "chi_mat_so",
    },
    "thoi_diem_dang_ky_truoc": {
        "đăng ký trước năm 2016": "truoc_2016",
        "trước 01/01/2016": "truoc_2016",
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
