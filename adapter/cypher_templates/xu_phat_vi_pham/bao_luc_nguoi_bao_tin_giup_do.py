"""Template — Bạo lực, trả thù người báo tin, ngăn chặn hoặc giúp đỡ Đ46 NĐ282."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates.xu_phat_vi_pham._params_common import (
    KhiaCanhCheTai,
    KHIA_CANH_CHE_TAI_FIELD,
)
from adapter.cypher_templates.xu_phat_vi_pham._seed_factory import make_parent_leaf_template

_LEAF_MAP: dict[str, str] = {
    "de_doa_can_tro": "de_doa_can_tro_nguoi_bao_tin_giup_do",
        "xuc_pham": "xuc_pham_nguoi_bao_tin_giup_do",
        "tra_thu_hanh_hung": "tra_thu_hanh_hung_nguoi_bao_tin_giup_do",
        "huy_hoai_tai_san": "huy_hoai_tai_san_nguoi_bao_tin_giup_do",
        "tong_quat": ""
}

_VPHC_WHITELIST = ['NghiDinh_282_2025_ND_CP_Dieu_46']
_HS_WHITELIST = []


class BaoLucNguoiBaoTinGiupDoParams(BaseModel):
    dang_hanh_vi: Literal["de_doa_can_tro","xuc_pham","tra_thu_hanh_hung","huy_hoai_tai_san","tong_quat"] = Field(description="trả thù người báo tin/giúp đỡ.")
    khia_canh_che_tai: KhiaCanhCheTai = KHIA_CANH_CHE_TAI_FIELD


bao_luc_nguoi_bao_tin_giup_do = make_parent_leaf_template(
    name="bao_luc_nguoi_bao_tin_giup_do",
    description='Bạo lực, trả thù người báo tin, ngăn chặn hoặc giúp đỡ Đ46 NĐ282.',
    params_schema=BaoLucNguoiBaoTinGiupDoParams,
    parent_id="quy_dinh_bao_luc_nguoi_bao_tin_giup_do",
    router_field="dang_hanh_vi",
    leaf_map=_LEAF_MAP,
    vphc_whitelist=_VPHC_WHITELIST,
    hs_whitelist=_HS_WHITELIST or None,
    dual_che_tai=False,
    hs_only=False,
)
