"""Template — Cưỡng ép thành viên gia đình ra khỏi chỗ ở hợp pháp Đ45 NĐ282."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from server.infrastructure.neo4j.cypher_templates.xu_phat_vi_pham._params_common import (
    KhiaCanhCheTai,
    KHIA_CANH_CHE_TAI_FIELD,
)
from server.infrastructure.neo4j.cypher_templates.xu_phat_vi_pham._seed_factory import make_parent_leaf_template

_LEAF_MAP: dict[str, str] = {
    "cuong_ep_thong_thuong": "cuong_ep_ra_khoi_cho_o_hop_phap",
        "de_doa_suc_khoe_tinh_mang": "de_doa_de_cuong_ep_ra_khoi_cho_o",
        "gay_thuong_tich_bang_cong_cu": "gay_thuong_tich_de_cuong_ep_ra_khoi_cho_o",
        "khong_ro": ""
}

_VPHC_WHITELIST = ['NghiDinh_282_2025_ND_CP_Dieu_45']
_HS_WHITELIST = []


class CuongEpRaKhoiChoOParams(BaseModel):
    muc_do: Literal["cuong_ep_thong_thuong","de_doa_suc_khoe_tinh_mang","gay_thuong_tich_bang_cong_cu","khong_ro"] = Field(description="đuổi khỏi nhà; dọa đe dọa; gây thương tích.")
    khia_canh_che_tai: KhiaCanhCheTai = KHIA_CANH_CHE_TAI_FIELD


cuong_ep_ra_khoi_cho_o = make_parent_leaf_template(
    name="cuong_ep_ra_khoi_cho_o",
    description='Cưỡng ép thành viên gia đình ra khỏi chỗ ở hợp pháp Đ45 NĐ282.',
    params_schema=CuongEpRaKhoiChoOParams,
    parent_id="quy_dinh_cuong_ep_ra_khoi_cho_o",
    router_field="muc_do",
    leaf_map=_LEAF_MAP,
    vphc_whitelist=_VPHC_WHITELIST,
    hs_whitelist=_HS_WHITELIST or None,
    dual_che_tai=False,
    hs_only=False,
)
