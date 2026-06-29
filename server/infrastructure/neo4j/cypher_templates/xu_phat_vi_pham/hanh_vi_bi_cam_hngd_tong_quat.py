"""Template — Hành vi bị cấm tại Điều 5 khoản 2 Luật HNGĐ (broad)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from server.infrastructure.neo4j.cypher_templates.xu_phat_vi_pham._hngd_dieu5 import NHOM_DIEU5_MAP
from server.infrastructure.neo4j.cypher_templates.xu_phat_vi_pham._seed_factory import make_parent_leaf_template

_NHOM_LEAF: dict[str, str] = {
    "ket_hon_ly_hon_gia_tao": "ket_hon_gia_tao_de_dat_muc_dich_khac",
    "tao_hon_cuong_ep_can_tro_ket_hon": "can_tro_ket_hon_hoac_ly_hon",
    "mot_vo_mot_chong": "ket_hon_khi_dang_co_vo_chong",
    "quan_he_hon_nhan_bi_cam": "ket_hon_chung_song_cung_dong_mau_truc_he_hoac_ba_doi",
    "yeu_sach_cua_cai": "yeu_sach_cua_cai_trong_ket_hon",
    "cuong_ep_can_tro_ly_hon": "cuong_ep_ket_hon_hoac_ly_hon",
    "sinh_con_mang_thai_ho": "lua_chon_gioi_tinh_thai_nhi",
    "bao_luc_gia_dinh": "danh_dap_xam_hai_suc_khoe_thanh_vien_gia_dinh",
    "loi_dung_quyen_hngd_truc_loi": "loi_dung_quyen_hngd_de_mua_ban_nguoi_truc_loi",
    "tong_quat": "",
}

_VPHC_WHITELIST = list(NHOM_DIEU5_MAP["tong_quat"])


class HanhViBiCamHngdTongQuatParams(BaseModel):
    nhom_hanh_vi_bi_cam: Literal[
        "ket_hon_ly_hon_gia_tao",
        "tao_hon_cuong_ep_can_tro_ket_hon",
        "mot_vo_mot_chong",
        "quan_he_hon_nhan_bi_cam",
        "yeu_sach_cua_cai",
        "cuong_ep_can_tro_ly_hon",
        "sinh_con_mang_thai_ho",
        "bao_luc_gia_dinh",
        "loi_dung_quyen_hngd_truc_loi",
        "tong_quat",
    ] = Field(
        description=(
            "Nhóm hành vi bị cấm tại Điều 5 khoản 2; "
            "'tong_quat' khi hỏi liệt kê toàn bộ hành vi bị cấm."
        )
    )


hanh_vi_bi_cam_hngd_tong_quat = make_parent_leaf_template(
    name="hanh_vi_bi_cam_hngd_tong_quat",
    description=(
        "Câu hỏi broad về hành vi bị cấm tại Điều 5 khoản 2 Luật HNGĐ 2014. "
        "Không thay template xử phạt cụ thể khi câu chỉ hỏi mức phạt/TNHS."
    ),
    params_schema=HanhViBiCamHngdTongQuatParams,
    parent_id="quy_dinh_hanh_vi_bi_cam_hngd",
    router_field="nhom_hanh_vi_bi_cam",
    leaf_map=_NHOM_LEAF,
    vphc_whitelist=_VPHC_WHITELIST,
    hs_whitelist=None,
    dual_che_tai=False,
    hs_only=False,
    fixed_loai_che_tai="vphc",
)
