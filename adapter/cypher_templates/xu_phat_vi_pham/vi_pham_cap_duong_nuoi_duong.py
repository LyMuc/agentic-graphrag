"""Template — Từ chối/trốn tránh cấp dưỡng, nuôi dưỡng. VPHC Đ43 và TNHS Đ186."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates.xu_phat_vi_pham._params_common import (
    LoaiCheTai,
    LOAI_CHE_TAI_FIELD,
    KhiaCanhCheTai,
    KHIA_CANH_CHE_TAI_FIELD,
)
from adapter.cypher_templates.xu_phat_vi_pham._seed_factory import make_parent_leaf_template

_LEAF_MAP: dict[str, str] = {
    "vo_chong_sau_ly_hon": "tron_tranh_cap_duong_vo_chong_hoac_nuoi_duong_ong_ba_chau_anh_chi_em",
        "cha_me_con": "tron_tranh_nuoi_duong_cha_me_cap_duong_cham_soc_con",
        "con_cha_me": "tron_tranh_nuoi_duong_cha_me_cap_duong_cham_soc_con",
        "ong_ba_chau": "tron_tranh_cap_duong_vo_chong_hoac_nuoi_duong_ong_ba_chau_anh_chi_em",
        "anh_chi_em": "tron_tranh_cap_duong_vo_chong_hoac_nuoi_duong_ong_ba_chau_anh_chi_em",
        "khong_ro": ""
}

_VPHC_WHITELIST = ['NghiDinh_282_2025_ND_CP_Dieu_43']
_HS_WHITELIST = ['BoLuat_HinhSu_2015_Dieu_186']


class ViPhamCapDuongNuoiDuongParams(BaseModel):
    quan_he_cap_duong: Literal["vo_chong_sau_ly_hon","cha_me_con","con_cha_me","ong_ba_chau","anh_chi_em","khong_ro"] = Field(description="không cấp dưỡng con/cha mẹ/vợ chồng sau ly hôn.")
    dang_nghia_vu: Literal["cap_duong","nuoi_duong","cham_soc","khong_ro"] = Field(description="cấp dưỡng/nuôi dưỡng/chăm sóc.")
    loai_che_tai: LoaiCheTai = LOAI_CHE_TAI_FIELD
    khia_canh_che_tai: KhiaCanhCheTai = KHIA_CANH_CHE_TAI_FIELD


vi_pham_cap_duong_nuoi_duong = make_parent_leaf_template(
    name="vi_pham_cap_duong_nuoi_duong",
    description='Từ chối/trốn tránh cấp dưỡng, nuôi dưỡng. VPHC Đ43 và TNHS Đ186.',
    params_schema=ViPhamCapDuongNuoiDuongParams,
    parent_id="quy_dinh_cap_duong_nuoi_duong",
    router_field="quan_he_cap_duong",
    leaf_map=_LEAF_MAP,
    vphc_whitelist=_VPHC_WHITELIST,
    hs_whitelist=_HS_WHITELIST or None,
    dual_che_tai=True,
    hs_only=False,
)
