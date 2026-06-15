"""Template — Cản trở, cưỡng ép, lừa dối kết hôn/ly hôn và yêu sách của cải/thách cưới"""
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
    "can_tro_ket_hon": "can_tro_ket_hon_hoac_ly_hon",
        "can_tro_ly_hon": "can_tro_ket_hon_hoac_ly_hon",
        "cuong_ep_ket_hon": "cuong_ep_ket_hon_hoac_ly_hon",
        "cuong_ep_ly_hon": "cuong_ep_ket_hon_hoac_ly_hon",
        "lua_doi_ket_hon": "lua_doi_ket_hon_hoac_ly_hon",
        "lua_doi_ly_hon": "lua_doi_ket_hon_hoac_ly_hon",
        "yeu_sach_cua_cai": "yeu_sach_cua_cai_trong_ket_hon",
        "tong_quat": ""
}

_VPHC_WHITELIST = ['NghiDinh_82_2020_ND_CP_Dieu_59_Khoan_1_Diem_đ', 'NghiDinh_82_2020_ND_CP_Dieu_59_Khoan_2_Diem_c']
_HS_WHITELIST = ['BoLuat_HinhSu_2015_Dieu_181']


class CanTroCuongEpKetHonLyHonParams(BaseModel):
    dang_hanh_vi: Literal["can_tro_ket_hon","can_tro_ly_hon","cuong_ep_ket_hon","cuong_ep_ly_hon","lua_doi_ket_hon","lua_doi_ly_hon","yeu_sach_cua_cai","tong_quat"] = Field(description="thách cưới → yeu_sach_cua_cai; ép ly hôn → cuong_ep_ly_hon.")
    loai_che_tai: LoaiCheTai = LOAI_CHE_TAI_FIELD
    khia_canh_che_tai: KhiaCanhCheTai = KHIA_CANH_CHE_TAI_FIELD


can_tro_cuong_ep_ket_hon_ly_hon = make_parent_leaf_template(
    name="can_tro_cuong_ep_ket_hon_ly_hon",
    description='Cản trở, cưỡng ép, lừa dối kết hôn/ly hôn và yêu sách của cải/thách cưới.',
    params_schema=CanTroCuongEpKetHonLyHonParams,
    parent_id="quy_dinh_can_tro_cuong_ep_ket_hon_ly_hon",
    router_field="dang_hanh_vi",
    leaf_map=_LEAF_MAP,
    vphc_whitelist=_VPHC_WHITELIST,
    hs_whitelist=_HS_WHITELIST or None,
    dual_che_tai=True,
    hs_only=False,
)
