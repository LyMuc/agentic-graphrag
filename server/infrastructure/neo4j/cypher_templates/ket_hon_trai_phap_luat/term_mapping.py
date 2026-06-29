"""Ánh xạ thuật ngữ thông thường → param chuẩn cho topic ket_hon_trai_phap_luat."""
from __future__ import annotations

import re
from typing import Any, Optional

COMMON_TO_LEGAL_TERMS: dict[str, dict[str, Any]] = {
    "khia_canh": {
        "là gì": "khai_niem",
        "thế nào là": "khai_niem",
        "trường hợp nào": "truong_hop_vi_pham",
        "bị coi là trái pháp luật": "truong_hop_vi_pham",
        "căn cứ hủy": "can_cu_huy",
        "dựa vào đâu để hủy": "can_cu_huy",
        "hợp đồng hôn nhân": "ranh_gioi_hanh_vi_bi_cam",
        "bảo vệ chế độ hôn nhân gia đình": "ranh_gioi_hanh_vi_bi_cam",
    },
    "dang_vi_pham": {
        "kết hôn giả để nhập hộ khẩu": "ket_hon_gia_tao_ngoai_core",
        "nhập cư": "ket_hon_gia_tao_ngoai_core",
        "tảo hôn": "chua_du_tuoi",
        "chưa đủ 18 tuổi": "chua_du_tuoi",
        "chưa đủ 20 tuổi": "chua_du_tuoi",
        "ép cưới": "khong_tu_nguyen_cuong_ep",
        "ép buộc kết hôn": "khong_tu_nguyen_cuong_ep",
        "cưỡng ép kết hôn": "khong_tu_nguyen_cuong_ep",
        "không tự nguyện": "khong_tu_nguyen_cuong_ep",
        "đe dọa": "lua_doi",
        "uy hiếp": "lua_doi",
        "che giấu sự thật": "lua_doi",
        "đã có vợ": "dang_co_vo_chong",
        "đã có chồng": "dang_co_vo_chong",
        "chưa ly hôn": "dang_co_vo_chong",
        "kết hôn lần hai": "dang_co_vo_chong",
    },
    "nhom_vi_pham": {
        "tảo hôn": "chua_du_tuoi",
        "chưa đủ tuổi": "chua_du_tuoi",
        "ép cưới": "cuong_ep_khong_tu_nguyen",
        "cưỡng ép": "cuong_ep_khong_tu_nguyen",
        "lừa dối": "lua_doi",
        "đe dọa": "lua_doi",
        "đã có vợ": "dang_co_vo_chong",
        "đã có chồng": "dang_co_vo_chong",
        "vừa chưa đủ tuổi vừa bị ép": "nhieu_vi_pham",
    },
    "chu_the_hoi_quyen": {
        "tôi bị ép": "nguoi_bi_cuong_ep_lua_doi",
        "tôi bị lừa": "nguoi_bi_cuong_ep_lua_doi",
        "người bị ép": "nguoi_bi_cuong_ep_lua_doi",
        "vợ trước": "vo_chong_hop_phap_cua_nguoi_dang_co_vo_chong",
        "chồng trước": "vo_chong_hop_phap_cua_nguoi_dang_co_vo_chong",
        "vợ hợp pháp": "vo_chong_hop_phap_cua_nguoi_dang_co_vo_chong",
        "cha mẹ": "cha_me",
        "bố mẹ": "cha_me",
        "người giám hộ": "nguoi_giam_ho_dai_dien",
        "người đại diện theo pháp luật": "nguoi_giam_ho_dai_dien",
        "hội phụ nữ": "hoi_lien_hiep_phu_nu",
        "hội liên hiệp phụ nữ": "hoi_lien_hiep_phu_nu",
        "cơ quan quản lý gia đình": "co_quan_quan_ly_gia_dinh",
        "cơ quan bảo vệ trẻ em": "co_quan_quan_ly_tre_em",
        "dì": "nguoi_than_thich_khac",
        "cô": "nguoi_than_thich_khac",
        "chú": "nguoi_than_thich_khac",
        "anh chị em": "nguoi_than_thich_khac",
        "hàng xóm": "ca_nhan_to_chuc_khac",
        "người quen": "ca_nhan_to_chuc_khac",
        "bạn bè": "ca_nhan_to_chuc_khac",
    },
    "vai_tro_tham_gia": {
        "tự mình yêu cầu": "tu_minh_yeu_cau",
        "có quyền yêu cầu trực tiếp": "yeu_cau_truc_tiep",
        "đề nghị hội phụ nữ": "de_nghi_co_quan_to_chuc",
        "đề nghị cơ quan": "de_nghi_co_quan_to_chuc",
        "báo cho": "de_nghi_co_quan_to_chuc",
    },
    "khia_canh_thu_tuc": {
        "cơ quan nào hủy": "tham_quyen_giai_quyet",
        "thẩm quyền hủy": "tham_quyen_giai_quyet",
        "hồ sơ gì": "ho_so_chung_cu",
        "giấy tờ gì": "ho_so_chung_cu",
        "chứng cứ gì": "ho_so_chung_cu",
        "mất giấy kết hôn": "that_lac_giay_chung_nhan",
        "thất lạc giấy chứng nhận": "that_lac_giay_chung_nhan",
        "chưa đăng ký": "phan_biet_khong_dang_ky_sai_tham_quyen",
        "chỉ sống chung": "phan_biet_khong_dang_ky_sai_tham_quyen",
        "đăng ký sai cơ quan": "phan_biet_khong_dang_ky_sai_tham_quyen",
    },
    "tinh_trang_dang_ky": {
        "đã đăng ký tại ubnd": "dung_tham_quyen",
        "cơ quan có thẩm quyền": "dung_tham_quyen",
        "đăng ký sai cơ quan": "sai_tham_quyen",
        "không đúng thẩm quyền": "sai_tham_quyen",
        "chưa đăng ký kết hôn": "khong_dang_ky",
        "chỉ sống chung": "khong_dang_ky",
    },
    "tinh_trang_giay_chung_nhan": {
        "mất giấy": "that_lac",
        "thất lạc": "that_lac",
        "chưa từng đăng ký": "khong_co_vi_khong_dang_ky",
    },
    "co_yeu_cau_giai_quyet_con_tai_san": {
        "con chung": "co",
        "tài sản": "co",
        "nghĩa vụ": "co",
        "hợp đồng": "co",
    },
    "trang_thai_dieu_kien_hien_tai": {
        "nay cả hai đã đủ tuổi": "ca_hai_da_du_dieu_kien",
        "đủ điều kiện": "ca_hai_da_du_dieu_kien",
        "vẫn chưa đủ tuổi": "van_co_ben_chua_du_dieu_kien",
        "vẫn chưa đủ điều kiện": "van_co_ben_chua_du_dieu_kien",
    },
    "yeu_cau_cua_hai_ben": {
        "cả hai đồng ý": "cung_yeu_cau_cong_nhan",
        "đều muốn duy trì": "cung_yeu_cau_cong_nhan",
        "cùng xin công nhận": "cung_yeu_cau_cong_nhan",
        "muốn hủy": "co_yeu_cau_huy",
        "cả hai xin ly hôn": "cung_yeu_cau_ly_hon",
        "một bên ly hôn": "mot_ben_ly_hon_ben_kia_cong_nhan",
    },
    "vi_pham_ban_dau": {
        "tảo hôn": "chua_du_tuoi",
        "chưa đủ tuổi": "chua_du_tuoi",
        "ép cưới": "khong_tu_nguyen_cuong_ep",
        "lừa dối": "lua_doi",
        "đã có vợ": "dang_co_vo_chong",
    },
    "ket_qua_nguoi_dung_hoi": {
        "được công nhận không": "cong_nhan",
        "có bị hủy không": "huy",
        "ra tòa ly hôn": "ly_hon",
    },
    "khia_canh_hau_qua": {
        "hậu quả pháp lý": "tong_quat",
        "chấm dứt sống như vợ chồng": "cham_dut_quan_he_nhu_vo_chong",
        "con chung": "quyen_nghia_vu_cha_me_con",
        "trách nhiệm với con": "quyen_nghia_vu_cha_me_con",
        "quyền nuôi con": "quyen_nghia_vu_cha_me_con",
        "chia tài sản": "tai_san_nghia_vu_hop_dong",
        "tài sản chung": "tai_san_nghia_vu_hop_dong",
        "nợ": "tai_san_nghia_vu_hop_dong",
        "hợp đồng": "tai_san_nghia_vu_hop_dong",
    },
    "co_con_chung": {
        "con chung": "co",
        "con nhỏ": "co",
    },
    "co_tranh_chap_tai_san": {
        "chia tài sản": "co",
        "nhà đất": "co",
        "tranh chấp tiền": "co",
    },
    "co_yeu_cau_thua_ke": {
        "thừa kế": "co",
        "di sản": "co",
        "người đã chết": "co",
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
