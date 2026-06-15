"""Template — Bạo lực tình dục trong gia đình Đ41 NĐ282."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates.xu_phat_vi_pham._params_common import (
    KhiaCanhCheTai,
    KHIA_CANH_CHE_TAI_FIELD,
)
from adapter.cypher_templates.xu_phat_vi_pham._seed_factory import make_parent_leaf_template

_LEAF_MAP: dict[str, str] = {
    "ep_tiep_nhan_noi_dung_khieu_dam": "cuong_ep_tiep_nhan_noi_dung_khieu_dam",
        "ep_trinh_dien_khieu_dam": "cuong_ep_trinh_dien_hanh_vi_khieu_dam",
        "ep_quan_he_tinh_duc_trai_y_muon": "cuong_ep_quan_he_tinh_duc_trai_y_muon_vo_chong",
        "tong_quat": ""
}

_VPHC_WHITELIST = ['NghiDinh_282_2025_ND_CP_Dieu_41']
_HS_WHITELIST = []


class BaoLucTinhDucParams(BaseModel):
    dang_hanh_vi: Literal["ep_tiep_nhan_noi_dung_khieu_dam","ep_trinh_dien_khieu_dam","ep_quan_he_tinh_duc_trai_y_muon","tong_quat"] = Field(description="bạo lực tình dục Đ41.")
    khia_canh_che_tai: KhiaCanhCheTai = KHIA_CANH_CHE_TAI_FIELD


bao_luc_tinh_duc = make_parent_leaf_template(
    name="bao_luc_tinh_duc",
    description='Bạo lực tình dục trong gia đình Đ41 NĐ282.',
    params_schema=BaoLucTinhDucParams,
    parent_id="quy_dinh_bao_luc_tinh_duc",
    router_field="dang_hanh_vi",
    leaf_map=_LEAF_MAP,
    vphc_whitelist=_VPHC_WHITELIST,
    hs_whitelist=_HS_WHITELIST or None,
    dual_che_tai=False,
    hs_only=False,
)
