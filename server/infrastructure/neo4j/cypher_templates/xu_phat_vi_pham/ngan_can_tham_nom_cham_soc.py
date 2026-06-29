"""Template — Ngăn cản quyền thăm nom, chăm sóc giữa thành viên gia đình Đ42 NĐ282."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from server.infrastructure.neo4j.cypher_templates.xu_phat_vi_pham._params_common import (
    KhiaCanhCheTai,
    KHIA_CANH_CHE_TAI_FIELD,
)
from server.infrastructure.neo4j.cypher_templates.xu_phat_vi_pham._seed_factory import make_parent_leaf_template

_LEAF_MAP: dict[str, str] = {
    "ong_ba_chau": "ngan_can_quyen_tham_nom_cham_soc",
        "cha_me_con": "ngan_can_quyen_tham_nom_cham_soc",
        "vo_chong": "ngan_can_quyen_tham_nom_cham_soc",
        "anh_chi_em": "ngan_can_quyen_tham_nom_cham_soc",
        "khong_ro": "ngan_can_quyen_tham_nom_cham_soc"
}

_VPHC_WHITELIST = ['NghiDinh_282_2025_ND_CP_Dieu_42']
_HS_WHITELIST = []


class NganCanThamNomChamSocParams(BaseModel):
    quan_he: Literal["ong_ba_chau","cha_me_con","vo_chong","anh_chi_em","khong_ro"] = Field(description="quan hệ bị ngăn thăm nom.")
    dang_quyen: Literal["tham_nom","cham_soc","ca_hai","khong_ro"] = Field(description="thăm nom/chăm sóc.")
    khia_canh_che_tai: KhiaCanhCheTai = KHIA_CANH_CHE_TAI_FIELD


ngan_can_tham_nom_cham_soc = make_parent_leaf_template(
    name="ngan_can_tham_nom_cham_soc",
    description='Ngăn cản quyền thăm nom, chăm sóc giữa thành viên gia đình Đ42 NĐ282.',
    params_schema=NganCanThamNomChamSocParams,
    parent_id="quy_dinh_ngan_can_tham_nom_cham_soc",
    router_field="quan_he",
    leaf_map=_LEAF_MAP,
    vphc_whitelist=_VPHC_WHITELIST,
    hs_whitelist=_HS_WHITELIST or None,
    dual_che_tai=False,
    hs_only=False,
)
