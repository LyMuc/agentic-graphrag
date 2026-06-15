"""Template — Bỏ mặc, không chăm sóc người yếu thế; không giáo dục trẻ em Đ38 NĐ282."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates.xu_phat_vi_pham._params_common import (
    KhiaCanhCheTai,
    KHIA_CANH_CHE_TAI_FIELD,
)
from adapter.cypher_templates.xu_phat_vi_pham._seed_factory import make_parent_leaf_template

_LEAF_MAP: dict[str, str] = {
    "bo_mac_khong_cham_soc": "bo_mac_khong_cham_soc_nguoi_can_cham_soc",
        "khong_giao_duc_tre_em": "khong_giao_duc_tre_em_trong_gia_dinh",
        "tong_quat": ""
}

_VPHC_WHITELIST = ['NghiDinh_282_2025_ND_CP_Dieu_38']
_HS_WHITELIST = []


class BoMacKhongChamSocGiaoDucParams(BaseModel):
    dang_hanh_vi: Literal["bo_mac_khong_cham_soc","khong_giao_duc_tre_em","tong_quat"] = Field(description="bỏ mặc; không giáo dục trẻ em.")
    doi_tuong: Literal["phu_nu_mang_thai","phu_nu_nuoi_con_duoi_36_thang","nguoi_khuyet_tat","nguoi_gia_yeu_cao_tuoi","nguoi_khong_tu_cham_soc","tre_em","khong_ro"] = Field(description="Đối tượng bị bỏ mặc.")
    khia_canh_che_tai: KhiaCanhCheTai = KHIA_CANH_CHE_TAI_FIELD


bo_mac_khong_cham_soc_giao_duc = make_parent_leaf_template(
    name="bo_mac_khong_cham_soc_giao_duc",
    description='Bỏ mặc, không chăm sóc người yếu thế; không giáo dục trẻ em Đ38 NĐ282.',
    params_schema=BoMacKhongChamSocGiaoDucParams,
    parent_id="quy_dinh_bo_mac_khong_cham_soc_giao_duc",
    router_field="dang_hanh_vi",
    leaf_map=_LEAF_MAP,
    vphc_whitelist=_VPHC_WHITELIST,
    hs_whitelist=_HS_WHITELIST or None,
    dual_che_tai=False,
    hs_only=False,
)
