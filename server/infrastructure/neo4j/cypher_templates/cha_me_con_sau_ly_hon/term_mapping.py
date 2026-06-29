"""Ánh xạ thuật ngữ thông thường → param chuẩn cho topic cha_me_con_sau_ly_hon."""
from __future__ import annotations

import re
from typing import Any, Optional

COMMON_TO_LEGAL_TERMS: dict[str, dict[str, Any]] = {
    "tinh_huong": {
        "giành quyền nuôi": "khong_thoa_thuan_toa_quyet_dinh",
        "tranh quyền nuôi": "khong_thoa_thuan_toa_quyet_dinh",
        "quyền nuôi con": "khong_thoa_thuan_toa_quyet_dinh",
        "hai bên thống nhất": "cha_me_thoa_thuan",
        "thỏa thuận người nuôi": "cha_me_thoa_thuan",
        "bố muốn nuôi": "cha_muon_truc_tiep_nuoi",
        "cha xin nuôi": "cha_muon_truc_tiep_nuoi",
        "mẹ muốn nuôi": "me_muon_truc_tiep_nuoi",
        "vợ xin nuôi": "me_muon_truc_tiep_nuoi",
        "chồng làm giám đốc": "so_sanh_dieu_kien_cha_me",
        "vợ nội trợ": "so_sanh_dieu_kien_cha_me",
        "thu nhập cao": "so_sanh_dieu_kien_cha_me",
        "thu nhập thấp": "so_sanh_dieu_kien_cha_me",
    },
    "yeu_to_trong_tam": {
        "lợi ích của con": "quyen_loi_moi_mat_cua_con",
        "quyền lợi mọi mặt": "quyen_loi_moi_mat_cua_con",
        "con chọn ở với ai": "nguyen_vong_cua_con",
        "hỏi ý kiến con": "nguyen_vong_cua_con",
        "nguyện vọng của con": "nguyen_vong_cua_con",
        "chăm sóc tốt": "dieu_kien_cham_soc",
        "chăm sóc không tốt": "dieu_kien_cham_soc",
        "bỏ mặc con": "dieu_kien_cham_soc",
    },
    "do_tuoi_con": {
        "con dưới 3 tuổi": "duoi_36_thang",
        "dưới 36 tháng": "duoi_36_thang",
        "con 9 tháng": "duoi_36_thang",
        "18 tháng": "duoi_36_thang",
        "24 tháng": "duoi_36_thang",
        "1 tuổi": "duoi_36_thang",
        "2 tuổi": "duoi_36_thang",
        "con từ đủ 7 tuổi": "tu_du_7_tuoi",
        "con 7 tuổi trở lên": "tu_du_7_tuoi",
        "con 9 tuổi": "tu_du_7_tuoi",
    },
    "tinh_trang_nguoi_me": {
        "mẹ không đủ điều kiện": "khong_du_dieu_kien",
        "mẹ không thể chăm con": "khong_du_dieu_kien",
        "mẹ bỏ đi": "khong_du_dieu_kien",
    },
    "thoa_thuan_khac": {
        "thỏa thuận để cha nuôi": "co",
        "hai bên thống nhất người nuôi": "co",
    },
    "ben_de_nghi_nuoi": {
        "bố muốn nuôi": "cha",
        "cha xin nuôi": "cha",
        "mẹ muốn nuôi": "me",
        "vợ xin nuôi": "me",
    },
    "khia_canh_nguoi_khong_truc_tiep": {
        "tôn trọng việc con ở với người nuôi": "ton_trong_quyen_song_chung",
        "bắt buộc chu cấp": "cap_duong_o_muc_nguyen_tac",
        "cấp dưỡng sau ly hôn": "cap_duong_o_muc_nguyen_tac",
        "quyền và nghĩa vụ gồm những gì": "quyen_nghia_vu_day_du",
        "quy định thế nào": "quyen_nghia_vu_day_du",
        "được thăm con": "tham_nom",
        "thăm nom": "tham_nom",
        "gặp con": "tham_nom",
    },
    "nguoi_khong_truc_tiep_nuoi": {
        "cha/bố/chồng cũ": "cha",
        "mẹ/vợ cũ": "me",
    },
    "tinh_trang_cap_duong": {
        "không cấp dưỡng": "khong_thuc_hien",
        "không chu cấp": "khong_thuc_hien",
        "đã chu cấp": "co_thuc_hien",
        "tranh chấp tiền": "dang_tranh_chap",
    },
    "co_can_tro_tham_nom": {
        "ngăn gặp con": "co",
        "cấm thăm con": "co",
        "cản trở thăm nom": "co",
        "không cho gặp con": "co",
    },
    "khia_canh_tham_nom": {
        "được gặp con": "quyen_tham_nom",
        "thăm con": "quyen_tham_nom",
        "ngăn gặp con": "can_tro_tham_nom",
        "cấm thăm con": "can_tro_tham_nom",
        "cản trở thăm nom": "can_tro_tham_nom",
        "lạm dụng thăm nom": "lam_dung_tham_nom",
        "gây ảnh hưởng xấu đến con": "lam_dung_tham_nom",
        "hạn chế quyền thăm nom": "yeu_cau_han_che_tham_nom",
        "bị phạt": "xu_ly_hanh_vi_can_tro",
        "xử lý thế nào": "xu_ly_hanh_vi_can_tro",
    },
    "chu_the_co_hanh_vi": {
        "vợ cũ cản": "nguoi_truc_tiep_nuoi",
        "chồng cũ cản": "nguoi_truc_tiep_nuoi",
        "ông bà cản": "thanh_vien_gia_dinh",
        "người nhà cản": "thanh_vien_gia_dinh",
    },
    "can_cu_thay_doi": {
        "đồng ý đổi người nuôi": "thoa_thuan_cua_cha_me",
        "thay đổi theo thỏa thuận": "thoa_thuan_cua_cha_me",
        "người đang nuôi chết": "nguoi_nuoi_khong_con_du_dieu_kien",
        "người đang nuôi mất": "nguoi_nuoi_khong_con_du_dieu_kien",
        "cả cha mẹ đều không đủ điều kiện": "ca_cha_me_khong_du_dieu_kien",
    },
    "nguoi_yeu_cau": {
        "ông bà nuôi cháu": "nguoi_than_thich",
        "cô dì chú cậu bác": "nguoi_than_thich",
        "anh chị em xin nuôi": "nguoi_than_thich",
        "hội phụ nữ": "hoi_lien_hiep_phu_nu",
        "hội liên hiệp phụ nữ": "hoi_lien_hiep_phu_nu",
        "cơ quan quản lý gia đình": "co_quan_quan_ly_gia_dinh",
        "cơ quan bảo vệ trẻ em": "co_quan_quan_ly_tre_em",
        "cơ quan quản lý trẻ em": "co_quan_quan_ly_tre_em",
    },
    "tinh_trang_nguoi_dang_nuoi": {
        "đi xuất khẩu lao động": "di_xa_khong_truc_tiep_cham_soc",
        "đi làm xa không chăm con": "di_xa_khong_truc_tiep_cham_soc",
        "đi tù": "di_tu",
        "chấp hành án phạt tù": "di_tu",
        "thất nghiệp": "that_nghiep_kho_khan",
        "phá sản": "that_nghiep_kho_khan",
        "kinh tế khó khăn": "that_nghiep_kho_khan",
        "nuôi không tốt": "cham_soc_khong_tot",
        "con thiếu thốn": "cham_soc_khong_tot",
        "bỏ bê": "cham_soc_khong_tot",
        "người đang nuôi chết": "chet",
        "người đang nuôi mất": "chet",
        "qua đời": "chet",
    },
    "ket_qua_de_nghi": {
        "giao cho người giám hộ": "giao_cho_nguoi_giam_ho",
        "ông bà nuôi cháu": "giao_cho_nguoi_than",
    },
    "pham_vi": {
        "trông nom": "trong_nom_cham_soc_nuoi_duong_giao_duc",
        "chăm sóc": "trong_nom_cham_soc_nuoi_duong_giao_duc",
        "nuôi dưỡng": "trong_nom_cham_soc_nuoi_duong_giao_duc",
        "giáo dục con": "trong_nom_cham_soc_nuoi_duong_giao_duc",
        "tước quyền làm cha": "tinh_trang_quyen_lam_cha_me",
        "tước quyền làm mẹ": "tinh_trang_quyen_lam_cha_me",
        "còn là cha mẹ không": "tinh_trang_quyen_lam_cha_me",
    },
    "tinh_trang_con": {
        "trẻ em": "chua_thanh_nien",
        "con nhỏ": "chua_thanh_nien",
        "mất năng lực hành vi dân sự": "thanh_nien_mat_nang_luc_hanh_vi",
        "không có khả năng lao động": "thanh_nien_khong_kha_nang_lao_dong_khong_tai_san",
    },
    "co_yeu_cau_cap_duong": {
        "cấp dưỡng": "co",
        "chu cấp": "co",
        "tiền nuôi con": "co",
    },
    "anh_huong_xau_den_con": {
        "gây ảnh hưởng xấu": "co",
        "cản trở chăm sóc": "co",
        "đe dọa con": "co",
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
