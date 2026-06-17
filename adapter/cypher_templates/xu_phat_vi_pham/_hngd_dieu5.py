"""Mapping Điều 5 khoản 2 Luật HNGĐ 2014 cho topic xu_phat_vi_pham.

Nguồn: docs/kg_xu_phat_vi_pham_schema.md §5.2–5.4, docs/xu_phat_vi_pham_templates_spec.md Phụ lục B.
"""
from __future__ import annotations

DIEU5_K2 = "Luat_HNGD_2014_Dieu_5_Khoan_2"
DIEU5_A = "Luat_HNGD_2014_Dieu_5_Khoan_2_Diem_a"
DIEU5_B = "Luat_HNGD_2014_Dieu_5_Khoan_2_Diem_b"
DIEU5_C = "Luat_HNGD_2014_Dieu_5_Khoan_2_Diem_c"
DIEU5_D = "Luat_HNGD_2014_Dieu_5_Khoan_2_Diem_d"
DIEU5_DD = "Luat_HNGD_2014_Dieu_5_Khoan_2_Diem_dd"
DIEU5_E = "Luat_HNGD_2014_Dieu_5_Khoan_2_Diem_e"
DIEU5_G = "Luat_HNGD_2014_Dieu_5_Khoan_2_Diem_g"
DIEU5_H = "Luat_HNGD_2014_Dieu_5_Khoan_2_Diem_h"
DIEU5_I = "Luat_HNGD_2014_Dieu_5_Khoan_2_Diem_i"

DIEU5_ALL_DIEMS: tuple[str, ...] = (
    DIEU5_A,
    DIEU5_B,
    DIEU5_C,
    DIEU5_D,
    DIEU5_DD,
    DIEU5_E,
    DIEU5_G,
    DIEU5_H,
    DIEU5_I,
)

# Bổ sung CAN_CU_TAI Điều 5 cho parent QuyDinh (schema §5.2).
PARENT_DIEU5_EXTRA: dict[str, list[str]] = {
    "quy_dinh_hanh_vi_bi_cam_hngd": list(DIEU5_ALL_DIEMS),
    "quy_dinh_ket_hon_ly_hon_tong_quat": [DIEU5_A, DIEU5_B, DIEU5_C, DIEU5_D],
    "quy_dinh_tao_hon": [DIEU5_B],
    "quy_dinh_mot_vo_mot_chong": [DIEU5_C],
    "quy_dinh_can_tro_cuong_ep_ket_hon_ly_hon": [DIEU5_B, DIEU5_DD, DIEU5_E],
    "quy_dinh_quan_he_hon_nhan_bi_cam_vphc": [DIEU5_D],
    "quy_dinh_ket_hon_ly_hon_gia_tao": [DIEU5_A],
    "quy_dinh_sinh_con_mang_thai_ho_thuong_mai": [DIEU5_G],
    "quy_dinh_vi_pham_giam_ho": [DIEU5_I],
    "quy_dinh_vi_pham_nuoi_con_nuoi": [DIEU5_I],
    "quy_dinh_bao_luc_the_chat_nguoc_dai": [DIEU5_H],
    "quy_dinh_bo_mac_khong_cham_soc_giao_duc": [DIEU5_H],
    "quy_dinh_xuc_pham_danh_du_bi_mat": [DIEU5_H],
    "quy_dinh_co_lap_ap_luc_tam_ly": [DIEU5_H],
    "quy_dinh_bao_luc_tinh_duc": [DIEU5_H, DIEU5_I],
    "quy_dinh_ngan_can_tham_nom_cham_soc": [DIEU5_H],
    "quy_dinh_cap_duong_nuoi_duong": [DIEU5_H],
    "quy_dinh_bao_luc_kinh_te": [DIEU5_H],
    "quy_dinh_cuong_ep_ra_khoi_cho_o": [DIEU5_H],
    "quy_dinh_bao_luc_nguoi_bao_tin_giup_do": [DIEU5_H],
    "quy_dinh_xui_giuc_cuong_ep_bao_luc": [DIEU5_H],
    "quy_dinh_ngan_chan_bao_tin_xu_ly": [DIEU5_H],
    "quy_dinh_truyen_ba_kich_dong_bao_luc": [DIEU5_H],
    "quy_dinh_tiet_lo_thong_tin_va_bang_gia": [DIEU5_H],
    "quy_dinh_loi_dung_hoat_dong_phong_chong_bao_luc": [DIEU5_H, DIEU5_I],
    "quy_dinh_dang_ky_co_so_tro_giup": [DIEU5_H],
    "quy_dinh_vi_pham_cam_tiep_xuc": [DIEU5_H],
}

# Bổ sung CAN_CU_TAI Điều 5 cho leaf semantic (schema §5.3–5.4).
LEAF_DIEU5_EXTRA: dict[str, list[str]] = {
    "to_chuc_lay_vo_chong_cho_nguoi_chua_du_tuoi": [DIEU5_B],
    "duy_tri_quan_he_vo_chong_voi_nguoi_chua_du_tuoi_sau_ban_an": [DIEU5_B],
    "ket_hon_khi_dang_co_vo_chong": [DIEU5_C],
    "chung_song_voi_nguoi_khac_khi_dang_co_vo_chong": [DIEU5_C],
    "chung_song_voi_nguoi_biet_ro_dang_co_vo_chong": [DIEU5_C],
    "mot_vo_mot_chong_lam_quan_he_hon_nhan_dan_den_ly_hon": [DIEU5_C],
    "mot_vo_mot_chong_lam_vo_chong_con_tu_sat": [DIEU5_C],
    "mot_vo_mot_chong_khong_chap_hanh_quyet_dinh_toa": [DIEU5_C],
    "can_tro_ket_hon_hoac_ly_hon": [DIEU5_B, DIEU5_E],
    "yeu_sach_cua_cai_trong_ket_hon": [DIEU5_DD],
    "cuong_ep_ket_hon_hoac_ly_hon": [DIEU5_B, DIEU5_E],
    "lua_doi_ket_hon_hoac_ly_hon": [DIEU5_B, DIEU5_E],
    "ket_hon_chung_song_quan_he_thong_gia_nuoi_duong_cu": [DIEU5_D],
    "ket_hon_chung_song_cung_dong_mau_truc_he_hoac_ba_doi": [DIEU5_D],
    "ket_hon_chung_song_cha_me_nuoi_con_nuoi": [DIEU5_D],
    "ket_hon_gia_tao_de_dat_muc_dich_khac": [DIEU5_A],
    "ly_hon_gia_tao_de_tron_nghia_vu": [DIEU5_A],
    "sinh_con_ho_tro_vi_muc_dich_thuong_mai": [DIEU5_G],
    "thuc_hien_sinh_san_vo_tinh": [DIEU5_G],
    "lua_chon_gioi_tinh_thai_nhi": [DIEU5_G],
    "mang_thai_ho_vi_muc_dich_thuong_mai": [DIEU5_G],
    "to_chuc_mang_thai_ho_vi_muc_dich_thuong_mai": [DIEU5_G],
    "loi_dung_giam_ho_xam_pham_tinh_duc_boc_lot": [DIEU5_I],
    "loi_dung_cho_nhan_gioi_thieu_con_nuoi_de_truc_loi": [DIEU5_I],
    "loi_dung_nhan_con_nuoi_de_boc_lot": [DIEU5_I],
    "loi_dung_quyen_hngd_de_mua_ban_nguoi_truc_loi": [DIEU5_I],
}

# Mọi leaf bạo lực gia đình NĐ282 (schema §5.4 — điểm h).
_BAO_LUC_LEAF_IDS = (
    "de_doa_xam_hai_suc_khoe_tinh_mang_thanh_vien_gia_dinh",
    "danh_dap_xam_hai_suc_khoe_thanh_vien_gia_dinh",
    "hanh_ha_nguoc_dai_thanh_vien_gia_dinh",
    "dung_cong_cu_gay_thuong_tich_thanh_vien_gia_dinh",
    "khong_cap_cuu_cham_soc_nan_nhan_bao_luc",
    "bo_mac_khong_cham_soc_nguoi_can_cham_soc",
    "khong_giao_duc_tre_em_trong_gia_dinh",
    "lang_ma_chiet_chi_xuc_pham_thanh_vien_gia_dinh",
    "phat_tan_bi_mat_doi_tu_de_xuc_pham",
    "ngan_can_gap_go_quan_he_xa_hoi_hop_phap",
    "ky_thi_phan_biet_hinh_the_gioi_tinh_nang_luc",
    "ngan_can_quyen_nghia_vu_trong_quan_he_gia_dinh",
    "cuong_ep_thanh_vien_hoc_tap_qua_suc",
    "cuong_ep_chung_kien_bao_luc_de_gay_ap_luc",
    "cuong_ep_tiep_nhan_noi_dung_kich_thich_bao_luc",
    "co_lap_giam_cam_thanh_vien_gia_dinh",
    "cuong_ep_tiep_nhan_noi_dung_khieu_dam",
    "cuong_ep_trinh_dien_hanh_vi_khieu_dam",
    "cuong_ep_quan_he_tinh_duc_trai_y_muon_vo_chong",
    "ngan_can_quyen_tham_nom_cham_soc",
    "tron_tranh_cap_duong_vo_chong_hoac_nuoi_duong_ong_ba_chau_anh_chi_em",
    "tron_tranh_nuoi_duong_cha_me_cap_duong_cham_soc_con",
    "chiem_doat_tai_san_gia_dinh",
    "huy_hoai_tai_san_gia_dinh",
    "cuong_ep_thanh_vien_lao_dong_qua_suc",
    "cuong_ep_dong_gop_tai_chinh_qua_kha_nang",
    "kiem_soat_tai_san_thu_nhap_tao_le_thuoc",
    "cuong_ep_ra_khoi_cho_o_hop_phap",
    "de_doa_de_cuong_ep_ra_khoi_cho_o",
    "gay_thuong_tich_de_cuong_ep_ra_khoi_cho_o",
    "de_doa_can_tro_nguoi_bao_tin_giup_do",
    "xuc_pham_nguoi_bao_tin_giup_do",
    "tra_thu_hanh_hung_nguoi_bao_tin_giup_do",
    "huy_hoai_tai_san_nguoi_bao_tin_giup_do",
    "xui_giuc_giup_suc_bao_luc_gia_dinh",
    "cuong_ep_nguoi_khac_bao_luc_gia_dinh",
    "biet_bao_luc_co_dieu_kien_nhung_khong_ngan_chan",
    "biet_bao_luc_nhung_khong_bao_tin",
    "dung_tung_bao_che_bao_luc_gia_dinh",
    "khong_bo_tri_truc_tong_dai_bao_luc_24_7",
    "vi_pham_quy_trinh_tiep_nhan_xu_ly_tin_bao_tong_dai",
    "can_tro_xu_ly_bao_luc_gia_dinh",
    "khong_xu_ly_hoac_xu_ly_sai_bao_luc_gia_dinh",
    "khong_chap_hanh_gop_y_hoac_phuc_vu_cong_dong",
    "truyen_ba_thong_tin_kich_dong_bao_luc_gia_dinh",
    "tiet_lo_noi_tam_lanh_cho_nguoi_bao_luc",
    "tiet_lo_thong_tin_nguoi_bao_tin_khong_dong_y",
    "khong_cong_khai_bang_gia_dich_vu_tro_giup",
    "doi_tien_sau_giup_do_hoac_thu_qua_gia_niem_yet",
    "yeu_cau_nan_nhan_tra_chi_phi_noi_tam_lanh",
    "loi_dung_hoan_canh_nan_nhan_de_yeu_cau_trai_luat",
    "lap_co_so_tro_giup_de_hoat_dong_co_loi_nhuan",
    "co_so_tro_giup_hoat_dong_ngoai_pham_vi_dang_ky",
    "co_so_tro_giup_hoat_dong_chua_dang_ky",
    "co_tinh_den_gan_nguoi_bi_cam_tiep_xuc",
    "dung_phuong_tien_de_bao_luc_nguoi_bi_cam_tiep_xuc",
)
for _lid in _BAO_LUC_LEAF_IDS:
    LEAF_DIEU5_EXTRA.setdefault(_lid, []).append(DIEU5_H)

LEAF_DIEU5_EXTRA["loi_dung_hoat_dong_phong_chong_bao_luc_de_trai_luat"] = [DIEU5_H, DIEU5_I]

# Template 3.29 — nhóm hành vi bị cấm → điểm Điều 5.
NHOM_DIEU5_MAP: dict[str, list[str]] = {
    "ket_hon_ly_hon_gia_tao": [DIEU5_A],
    "tao_hon_cuong_ep_can_tro_ket_hon": [DIEU5_B],
    "mot_vo_mot_chong": [DIEU5_C],
    "quan_he_hon_nhan_bi_cam": [DIEU5_D],
    "yeu_sach_cua_cai": [DIEU5_DD],
    "cuong_ep_can_tro_ly_hon": [DIEU5_E],
    "sinh_con_mang_thai_ho": [DIEU5_G],
    "bao_luc_gia_dinh": [DIEU5_H],
    "loi_dung_quyen_hngd_truc_loi": [DIEU5_I],
    "tong_quat": [DIEU5_K2, *DIEU5_ALL_DIEMS],
}

# Whitelist broad theo template (Phụ lục B) — chỉ phần Luật HNGĐ Điều 5 bổ sung.
TEMPLATE_BROAD_DIEU5: dict[str, list[str]] = {
    "xu_phat_ket_hon_ly_hon_tong_quat": [DIEU5_A, DIEU5_B, DIEU5_C, DIEU5_D],
    "tao_hon_va_to_chuc_tao_hon": [DIEU5_B],
    "vi_pham_mot_vo_mot_chong": [DIEU5_C],
    "can_tro_cuong_ep_ket_hon_ly_hon": [DIEU5_B, DIEU5_DD, DIEU5_E],
    "quan_he_hon_nhan_bi_cam_vphc": [DIEU5_D],
    "toi_loan_luan_hinh_su": [DIEU5_D],
    "ket_hon_ly_hon_gia_tao": [DIEU5_A],
    "sinh_con_mang_thai_ho_thuong_mai": [DIEU5_G],
    "vi_pham_giam_ho": [DIEU5_I],
    "vi_pham_nuoi_con_nuoi": [DIEU5_I],
    "bao_luc_the_chat_nguoc_dai": [DIEU5_H],
    "bo_mac_khong_cham_soc_giao_duc": [DIEU5_H],
    "xuc_pham_danh_du_bi_mat": [DIEU5_H],
    "co_lap_ap_luc_tam_ly": [DIEU5_H],
    "bao_luc_tinh_duc": [DIEU5_H, DIEU5_I],
    "ngan_can_tham_nom_cham_soc": [DIEU5_H],
    "vi_pham_cap_duong_nuoi_duong": [DIEU5_H],
    "bao_luc_kinh_te": [DIEU5_H],
    "cuong_ep_ra_khoi_cho_o": [DIEU5_H],
    "bao_luc_nguoi_bao_tin_giup_do": [DIEU5_H],
    "xui_giuc_cuong_ep_bao_luc": [DIEU5_H],
    "vi_pham_ngan_chan_bao_tin_xu_ly": [DIEU5_H],
    "truyen_ba_kich_dong_bao_luc": [DIEU5_H],
    "tiet_lo_thong_tin_va_bang_gia": [DIEU5_H],
    "loi_dung_hoat_dong_phong_chong_bao_luc": [DIEU5_H, DIEU5_I],
    "vi_pham_dang_ky_co_so_tro_giup": [DIEU5_H],
    "vi_pham_cam_tiep_xuc": [DIEU5_H],
}


def _dedupe(ids: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in ids:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def dieu5_for_leaf(leaf_id: str) -> list[str]:
    if not leaf_id:
        return []
    return list(LEAF_DIEU5_EXTRA.get(leaf_id, []))


def merge_dieu5_can_cu(legal_ids: list[str], semantic_id: str) -> list[str]:
    extra = PARENT_DIEU5_EXTRA.get(semantic_id) or LEAF_DIEU5_EXTRA.get(semantic_id) or []
    return _dedupe(list(legal_ids) + list(extra))


__all__ = [
    "DIEU5_K2",
    "DIEU5_ALL_DIEMS",
    "LEAF_DIEU5_EXTRA",
    "NHOM_DIEU5_MAP",
    "PARENT_DIEU5_EXTRA",
    "TEMPLATE_BROAD_DIEU5",
    "dieu5_for_leaf",
    "merge_dieu5_can_cu",
]
