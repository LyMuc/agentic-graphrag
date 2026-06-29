"""Template — Tảo hôn, tổ chức hôn lễ cho người chưa đủ tuổi, duy trì quan hệ sau bản """
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from server.infrastructure.neo4j.cypher_templates.xu_phat_vi_pham._params_common import (
    LoaiCheTai,
    LOAI_CHE_TAI_FIELD,
    KhiaCanhCheTai,
    KHIA_CANH_CHE_TAI_FIELD,
)
from server.infrastructure.neo4j.cypher_templates.xu_phat_vi_pham._seed_factory import make_parent_leaf_template

_LEAF_MAP: dict[str, str] = {
    "ket_hon_chua_du_tuoi": "to_chuc_lay_vo_chong_cho_nguoi_chua_du_tuoi",
        "to_chuc_tao_hon": "to_chuc_lay_vo_chong_cho_nguoi_chua_du_tuoi",
        "duy_tri_sau_ban_an": "duy_tri_quan_he_vo_chong_voi_nguoi_chua_du_tuoi_sau_ban_an",
        "tong_quat": ""
}

_VPHC_WHITELIST = ['NghiDinh_82_2020_ND_CP_Dieu_58']
_HS_WHITELIST = ['BoLuat_HinhSu_2015_Dieu_183']


class TaoHonVaToChucTaoHonParams(BaseModel):
    dang_hanh_vi: Literal["ket_hon_chua_du_tuoi","to_chuc_tao_hon","duy_tri_sau_ban_an","tong_quat"] = Field(description="tảo hôn/chưa đủ tuổi; tổ chức hôn lễ; duy trì sau bản án.")
    loai_che_tai: LoaiCheTai = LOAI_CHE_TAI_FIELD
    khia_canh_che_tai: KhiaCanhCheTai = KHIA_CANH_CHE_TAI_FIELD


tao_hon_va_to_chuc_tao_hon = make_parent_leaf_template(
    name="tao_hon_va_to_chuc_tao_hon",
    description='Tảo hôn, tổ chức hôn lễ cho người chưa đủ tuổi, duy trì quan hệ sau bản án. Phân biệt VPHC Đ58 và TNHS Đ183.',
    params_schema=TaoHonVaToChucTaoHonParams,
    parent_id="quy_dinh_tao_hon",
    router_field="dang_hanh_vi",
    leaf_map=_LEAF_MAP,
    vphc_whitelist=_VPHC_WHITELIST,
    hs_whitelist=_HS_WHITELIST or None,
    dual_che_tai=True,
    hs_only=False,
)
