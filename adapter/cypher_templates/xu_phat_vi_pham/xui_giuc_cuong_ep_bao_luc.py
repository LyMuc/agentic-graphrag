"""Template — Kích động, xúi giục, cưỡng ép người khác bạo lực gia đình Đ47 NĐ282."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates.xu_phat_vi_pham._params_common import (
    KhiaCanhCheTai,
    KHIA_CANH_CHE_TAI_FIELD,
)
from adapter.cypher_templates.xu_phat_vi_pham._seed_factory import make_parent_leaf_template

_LEAF_MAP: dict[str, str] = {
    "kich_dong_xui_giuc": "xui_giuc_giup_suc_bao_luc_gia_dinh",
        "loi_keo_du_do": "xui_giuc_giup_suc_bao_luc_gia_dinh",
        "giup_suc": "xui_giuc_giup_suc_bao_luc_gia_dinh",
        "cuong_ep_nguoi_khac": "cuong_ep_nguoi_khac_bao_luc_gia_dinh",
        "khong_ro": ""
}

_VPHC_WHITELIST = ['NghiDinh_282_2025_ND_CP_Dieu_47']
_HS_WHITELIST = []


class XuiGiucCuongEpBaoLucParams(BaseModel):
    vai_tro: Literal["kich_dong_xui_giuc","loi_keo_du_do","giup_suc","cuong_ep_nguoi_khac","khong_ro"] = Field(description="xúi giục/giúp sức; cưỡng ép người khác.")
    khia_canh_che_tai: KhiaCanhCheTai = KHIA_CANH_CHE_TAI_FIELD


xui_giuc_cuong_ep_bao_luc = make_parent_leaf_template(
    name="xui_giuc_cuong_ep_bao_luc",
    description='Kích động, xúi giục, cưỡng ép người khác bạo lực gia đình Đ47 NĐ282.',
    params_schema=XuiGiucCuongEpBaoLucParams,
    parent_id="quy_dinh_xui_giuc_cuong_ep_bao_luc",
    router_field="vai_tro",
    leaf_map=_LEAF_MAP,
    vphc_whitelist=_VPHC_WHITELIST,
    hs_whitelist=_HS_WHITELIST or None,
    dual_che_tai=False,
    hs_only=False,
)
