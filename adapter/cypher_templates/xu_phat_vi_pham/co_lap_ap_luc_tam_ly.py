"""Template — Cô lập, giam cầm, kỳ thị, gây áp lực tâm lý Đ40 NĐ282."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates.xu_phat_vi_pham._params_common import (
    KhiaCanhCheTai,
    KHIA_CANH_CHE_TAI_FIELD,
)
from adapter.cypher_templates.xu_phat_vi_pham._seed_factory import make_parent_leaf_template

_LEAF_MAP: dict[str, str] = {
    "ngan_gap_go": "ngan_can_gap_go_quan_he_xa_hoi_hop_phap",
        "ky_thi_phan_biet": "ky_thi_phan_biet_hinh_the_gioi_tinh_nang_luc",
        "ngan_quyen_nghia_vu": "ngan_can_quyen_nghia_vu_trong_quan_he_gia_dinh",
        "ep_hoc_qua_suc": "cuong_ep_thanh_vien_hoc_tap_qua_suc",
        "ep_chung_kien_bao_luc": "cuong_ep_chung_kien_bao_luc_de_gay_ap_luc",
        "ep_tiep_nhan_noi_dung_bao_luc": "cuong_ep_tiep_nhan_noi_dung_kich_thich_bao_luc",
        "co_lap_giam_cam": "co_lap_giam_cam_thanh_vien_gia_dinh",
        "tong_quat": ""
}

_VPHC_WHITELIST = ['NghiDinh_282_2025_ND_CP_Dieu_40']
_HS_WHITELIST = []


class CoLapApLucTamLyParams(BaseModel):
    dang_hanh_vi: Literal["ngan_gap_go","ky_thi_phan_biet","ngan_quyen_nghia_vu","ep_hoc_qua_suc","ep_chung_kien_bao_luc","ep_tiep_nhan_noi_dung_bao_luc","co_lap_giam_cam","tong_quat"] = Field(description="cô lập, giam cầm, áp lực tâm lý Đ40.")
    khia_canh_che_tai: KhiaCanhCheTai = KHIA_CANH_CHE_TAI_FIELD


co_lap_ap_luc_tam_ly = make_parent_leaf_template(
    name="co_lap_ap_luc_tam_ly",
    description='Cô lập, giam cầm, kỳ thị, gây áp lực tâm lý Đ40 NĐ282.',
    params_schema=CoLapApLucTamLyParams,
    parent_id="quy_dinh_co_lap_ap_luc_tam_ly",
    router_field="dang_hanh_vi",
    leaf_map=_LEAF_MAP,
    vphc_whitelist=_VPHC_WHITELIST,
    hs_whitelist=_HS_WHITELIST or None,
    dual_che_tai=False,
    hs_only=False,
)
