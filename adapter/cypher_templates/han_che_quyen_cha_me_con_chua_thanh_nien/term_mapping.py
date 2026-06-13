"""Ánh xạ thuật ngữ thông thường → param chuẩn cho topic han_che_quyen."""
from __future__ import annotations

import re
from typing import Any, Optional

COMMON_TO_LEGAL_TERMS: dict[str, dict[str, Any]] = {
    "doi_tuong_bi_han_che": {
        "bố": "cha",
        "cha": "cha",
        "quyền làm cha": "cha",
        "mẹ": "me",
        "quyền làm mẹ": "me",
        "cha mẹ": "cha_hoac_me",
        "cha hoặc mẹ": "cha_hoac_me",
    },
    "khia_canh_han_che": {
        "trường hợp nào": "truong_hop",
        "khi nào bị hạn chế": "truong_hop",
        "có bị hạn chế": "doi_chieu_tinh_huong",
        "bị hạn chế những quyền gì": "pham_vi_quyen",
        "tước những quyền gì": "pham_vi_quyen",
        "hạn chế bao lâu": "thoi_han",
        "mấy năm": "thoi_han",
        "rút ngắn thời hạn": "rut_ngan_thoi_han",
        "xin giảm thời hạn": "rut_ngan_thoi_han",
    },
    "nhom_can_cu_hanh_vi": {
        "đi tù": "bi_ket_an_khong_ro_toi_danh",
        "ở tù": "bi_ket_an_khong_ro_toi_danh",
        "chấp hành án": "bi_ket_an_khong_ro_toi_danh",
        "cố ý đánh con": "bi_ket_an_xam_pham_con",
        "xâm phạm con": "bi_ket_an_xam_pham_con",
        "bỏ bê con": "vi_pham_nghiem_trong_nghia_vu_voi_con",
        "không chăm sóc nuôi dưỡng": "vi_pham_nghiem_trong_nghia_vu_voi_con",
        "phá tài sản của con": "pha_tan_tai_san_cua_con",
        "tiêu tán tài sản": "pha_tan_tai_san_cua_con",
        "lối sống đồi trụy": "loi_song_doi_truy",
        "ăn chơi đồi trụy": "loi_song_doi_truy",
        "xúi giục con": "xui_giuc_ep_buoc_con",
        "ép con làm việc phạm pháp": "xui_giuc_ep_buoc_con",
    },
    "quyen_bi_hoi": {
        "trông nom": "trong_nom",
        "thăm nom": "tham_nom_cach_noi_doi_thuong",
        "chăm sóc con": "cham_soc",
        "giáo dục con": "giao_duc",
        "dạy dỗ": "giao_duc",
        "quản lý tài sản": "quan_ly_tai_san_rieng",
        "đại diện pháp luật": "dai_dien_theo_phap_luat",
        "đại diện cho con": "dai_dien_theo_phap_luat",
    },
    "nhom_chu_the_yeu_cau": {
        "người giám hộ": "nguoi_giam_ho",
        "ông bà": "nguoi_than_thich",
        "người thân": "nguoi_than_thich",
        "người thân thích": "nguoi_than_thich",
        "cơ quan gia đình": "co_quan_quan_ly_gia_dinh",
        "cơ quan trẻ em": "co_quan_quan_ly_tre_em",
        "hội phụ nữ": "hoi_lien_hiep_phu_nu",
        "hội liên hiệp phụ nữ": "hoi_lien_hiep_phu_nu",
        "hàng xóm": "ca_nhan_co_quan_to_chuc_khac",
        "người phát hiện": "ca_nhan_co_quan_to_chuc_khac",
    },
    "khia_canh_yeu_cau": {
        "ai được nộp đơn": "danh_sach_chu_the",
        "ai được yêu cầu tòa án": "danh_sach_chu_the",
        "đề nghị cơ quan": "co_quyen_de_nghi",
        "báo cơ quan nào": "co_quyen_de_nghi",
    },
    "tinh_trang_cha_me": {
        "chỉ bố bị hạn chế": "mot_ben_bi_han_che",
        "chỉ mẹ bị hạn chế": "mot_ben_bi_han_che",
        "cả bố mẹ": "ca_hai_bi_han_che",
        "cả cha mẹ đều bị hạn chế": "ca_hai_bi_han_che",
        "người còn lại không đủ điều kiện": "ben_con_lai_khong_du_dieu_kien",
        "không xác định được bố mẹ": "khong_xac_dinh_ben_con_lai",
    },
    "khia_canh_hau_qua": {
        "ai chăm con": "ben_con_lai_thuc_hien_quyen",
        "ai đại diện cho con": "ben_con_lai_thuc_hien_quyen",
        "giao cho người giám hộ": "giao_nguoi_giam_ho",
        "ai làm giám hộ": "giao_nguoi_giam_ho",
        "còn phải cấp dưỡng": "nghia_vu_cap_duong",
        "chu cấp tiền nuôi con": "nghia_vu_cap_duong",
    },
    "boi_canh_nuoi_con": {
        "sau ly hôn": "sau_ly_hon",
        "giành quyền nuôi": "sau_ly_hon",
        "bị hạn chế quyền": "han_che_quyen",
        "bị tòa án hạn chế": "han_che_quyen",
        "mẹ không được nuôi con": "giao_thoa",
        "mất quyền nuôi con": "giao_thoa",
    },
    "do_tuoi_con": {
        "dưới 3 tuổi": "duoi_36_thang",
        "dưới 36 tháng": "duoi_36_thang",
        "từ đủ 7 tuổi": "tu_du_7_tuoi",
        "từ 7 tuổi": "tu_du_7_tuoi",
    },
    "khia_canh_nuoi_con": {
        "mẹ không đủ điều kiện": "me_khong_du_dieu_kien",
        "nguyện vọng của con": "nguyen_vong_cua_con",
        "ý kiến của con": "nguyen_vong_cua_con",
        "cha mẹ thỏa thuận": "thoa_thuan",
    },
}

_SKIP_VALUES = frozenset({"khong_ro", "chua_ro", "tat_ca", "tong_quat"})


def resolve_term(field: str, raw_text: str) -> Optional[str]:
    mapping = COMMON_TO_LEGAL_TERMS.get(field)
    if not mapping or not raw_text:
        return None
    text = re.sub(r"\s+", " ", raw_text.lower()).strip()
    best_key = ""
    best_val = None
    for key, val in mapping.items():
        if key in text and len(key) > len(best_key):
            best_key = key
            best_val = val
    return best_val


def resolve_many(field: str, raw_text: str) -> list[str]:
    val = resolve_term(field, raw_text)
    return [val] if val else []


__all__ = ["COMMON_TO_LEGAL_TERMS", "resolve_term", "resolve_many"]
