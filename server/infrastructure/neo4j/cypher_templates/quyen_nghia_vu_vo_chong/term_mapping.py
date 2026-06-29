"""Ánh xạ thuật ngữ thông thường → param chuẩn cho topic quyen_nghia_vu_vo_chong."""
from __future__ import annotations

import re
from typing import Any, Optional

COMMON_TO_LEGAL_TERMS: dict[str, dict[str, Any]] = {
    "khia_canh_binh_dang": {
        "quyền và nghĩa vụ ngang nhau": "quyen_nghia_vu_ngang_nhau",
        "bình đẳng mọi mặt trong gia đình": "pham_vi_moi_mat_trong_gia_dinh",
        "mọi mặt trong gia đình": "pham_vi_moi_mat_trong_gia_dinh",
        "tự quyết mọi việc": "quyet_dinh_cong_viec_gia_dinh",
        "chồng tự quyết mọi việc": "quyet_dinh_cong_viec_gia_dinh",
        "vợ tự quyết mọi việc": "quyet_dinh_cong_viec_gia_dinh",
        "bình đẳng": "quyen_nghia_vu_ngang_nhau",
        "ngang nhau": "quyen_nghia_vu_ngang_nhau",
    },
    "chu_the_quyet_dinh": {
        "vợ chồng": "ca_hai_vo_chong",
        "chồng tự quyết": "chong",
        "chồng quyết định": "chong",
        "vợ tự quyết": "vo",
    },
    "dang_xam_pham_nhan_than": {
        "can thiệp quyền tự do cá nhân": "can_thiep_quyen_tu_do_ca_nhan",
        "được tôn trọng và bảo vệ": "hoi_co_che_bao_ve",
        "quyền nhân thân được bảo vệ": "hoi_co_che_bao_ve",
        "tôn trọng và bảo vệ": "hoi_co_che_bao_ve",
    },
    "chu_the_can_thiep": {
        "gia đình chồng": "gia_dinh_chong",
        "gia đình vợ": "gia_dinh_vo",
    },
    "khia_canh_tinh_nghia": {
        "chung thủy": "chung_thuy",
        "quan hệ tình cảm với người khác": "chung_thuy",
        "ngoại tình": "chung_thuy",
        "thương yêu": "thuong_yeu",
        "quan tâm, chăm sóc, giúp đỡ": "ton_trong_quan_tam_cham_soc_giup_do",
        "chăm sóc": "ton_trong_quan_tam_cham_soc_giup_do",
        "giúp đỡ": "ton_trong_quan_tam_cham_soc_giup_do",
        "công việc gia đình": "chia_se_cong_viec_gia_dinh",
        "chia sẻ công việc gia đình": "chia_se_cong_viec_gia_dinh",
        "nhẫn cưới": "khong_deo_nhan_cuoi",
        "không đeo nhẫn cưới": "khong_deo_nhan_cuoi",
        "có những nghĩa vụ gì": "liet_ke_nghia_vu",
        "tình nghĩa vợ chồng": "tong_quat",
    },
    "pham_vi_tinh_nghia": {
        "tình nghĩa vợ chồng": "toan_bo_dieu_19",
        "khoản 1 điều 19": "khoan_1",
        "điều 19 khoản 1": "khoan_1",
    },
    "tinh_huong_song_chung": {
        "bắt buộc sống chung": "bat_buoc_song_chung",
        "thỏa thuận không sống chung": "thoa_thuan_song_rieng",
        "sống riêng": "thoa_thuan_song_rieng",
        "ly thân": "thoa_thuan_song_rieng",
        "đi làm ở tỉnh khác": "nghe_nghiep_cong_tac",
        "công tác xa": "nghe_nghiep_cong_tac",
        "đi học xa": "hoc_tap",
        "lý do chính đáng": "ly_do_chinh_dang_khac",
    },
    "khia_canh_song_chung": {
        "có bắt buộc không": "co_nghia_vu",
        "bắt buộc không": "co_nghia_vu",
        "có được công nhận không": "co_thuoc_ngoai_le",
        "lý do chính đáng không": "danh_gia_ly_do",
    },
    "tinh_huong_cu_tru": {
        "chuyển khẩu": "chuyen_khau_ve_nha_chong",
        "nhập khẩu về nhà chồng": "chuyen_khau_ve_nha_chong",
        "cắt khẩu về nhà chồng": "chuyen_khau_ve_nha_chong",
        "ở chung gia đình chồng": "o_chung_gia_dinh_chong",
        "về ở chung với gia đình chồng": "o_chung_gia_dinh_chong",
        "chồng quyết định nơi cư trú": "chong_tu_quyet_noi_cu_tru",
        "chồng tự quyết nơi cư trú": "chong_tu_quyet_noi_cu_tru",
        "phong tục": "phong_tuc_tap_quan_va_dia_gioi_hanh_chinh",
        "tập quán": "phong_tuc_tap_quan_va_dia_gioi_hanh_chinh",
        "địa giới hành chính": "phong_tuc_tap_quan_va_dia_gioi_hanh_chinh",
        "nơi thường xuyên chung sống": "noi_thuong_xuyen_chung_song",
        "nơi cư trú khác nhau": "noi_cu_tru_khac_nhau",
    },
    "khia_canh_cu_tru": {
        "do ai quyết định": "ai_quyet_dinh",
        "ai quyết định": "ai_quyet_dinh",
        "có bắt buộc": "co_bat_buoc",
        "có nơi cư trú khác nhau": "co_duoc_o_khac_nhau",
        "nơi cư trú là đâu": "xac_dinh_noi_cu_tru",
        "bị ràng buộc": "co_bi_rang_buoc",
    },
    "hanh_vi_danh_du": {
        "đăng thông tin riêng tư lên mạng": "dang_thong_tin_rieng_tu_len_mang",
        "đăng lên mạng": "dang_thong_tin_rieng_tu_len_mang",
        "tôn trọng, giữ gìn, bảo vệ": "liet_ke_nghia_vu",
        "danh dự": "liet_ke_nghia_vu",
        "nhân phẩm": "liet_ke_nghia_vu",
        "uy tín": "liet_ke_nghia_vu",
    },
    "doi_tuong_bi_anh_huong": {
        "danh dự vợ": "vo",
        "của vợ": "vo",
        "danh dự chồng": "chong",
        "của chồng": "chong",
    },
    "hanh_vi_tin_nguong": {
        "cấm đi lễ": "cam_can_thuc_hanh_ton_giao",
        "cấm theo đạo": "cam_can_thuc_hanh_ton_giao",
        "cấm cản đi lễ": "cam_can_thuc_hanh_ton_giao",
        "ép theo đạo": "ep_buoc_theo_ton_giao",
        "ép theo tôn giáo": "ep_buoc_theo_ton_giao",
        "tự do tín ngưỡng": "liet_ke_nghia_vu",
        "tự do tôn giáo": "liet_ke_nghia_vu",
    },
    "linh_vuc_hoat_dong": {
        "chọn nghề nghiệp": "chon_nghe_nghiep",
        "đi làm": "lam_viec_kiem_tien",
        "kiếm tiền": "lam_viec_kiem_tien",
        "cấm đi làm": "lam_viec_kiem_tien",
        "học tập": "hoc_tap_nang_cao_trinh_do",
        "nâng cao trình độ": "hoc_tap_nang_cao_trinh_do",
        "hoạt động chính trị": "hoat_dong_chinh_tri_kinh_te_van_hoa_xa_hoi",
        "hoạt động kinh tế": "hoat_dong_chinh_tri_kinh_te_van_hoa_xa_hoi",
        "hoạt động văn hóa": "hoat_dong_chinh_tri_kinh_te_van_hoa_xa_hoi",
        "hoạt động xã hội": "hoat_dong_chinh_tri_kinh_te_van_hoa_xa_hoi",
        "nghề nghiệp và học tập": "nhieu_linh_vuc",
    },
    "dang_hanh_vi": {
        "tạo điều kiện": "tao_dieu_kien_giup_do",
        "giúp đỡ": "tao_dieu_kien_giup_do",
        "cấm đi làm": "cam_can_han_che",
        "cản trở học tập": "cam_can_han_che",
        "chồng không đồng ý": "khong_dong_y",
        "vợ không đồng ý": "khong_dong_y",
        "quyền nghĩa vụ": "hoi_quyen_nghia_vu",
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
