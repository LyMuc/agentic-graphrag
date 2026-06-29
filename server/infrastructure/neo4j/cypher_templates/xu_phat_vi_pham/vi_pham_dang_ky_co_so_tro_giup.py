"""Template — Cơ sở trợ giúp hoạt động ngoài phạm vi hoặc chưa đăng ký Đ52 NĐ282."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from server.infrastructure.neo4j.cypher_templates.xu_phat_vi_pham._params_common import (
    KhiaCanhCheTai,
    KHIA_CANH_CHE_TAI_FIELD,
)
from server.infrastructure.neo4j.cypher_templates.xu_phat_vi_pham._seed_factory import make_parent_leaf_template

_LEAF_MAP: dict[str, str] = {
    "ngoai_pham_vi": "co_so_tro_giup_hoat_dong_ngoai_pham_vi_dang_ky",
        "chua_duoc_cap": "co_so_tro_giup_hoat_dong_chua_dang_ky",
        "khong_dang_ky": "co_so_tro_giup_hoat_dong_chua_dang_ky",
        "khong_ro": ""
}

_VPHC_WHITELIST = ['NghiDinh_282_2025_ND_CP_Dieu_52']
_HS_WHITELIST = []


class ViPhamDangKyCoSoTroGiupParams(BaseModel):
    tinh_trang_dang_ky: Literal["ngoai_pham_vi","chua_duoc_cap","khong_dang_ky","khong_ro"] = Field(description="ngoài phạm vi; chưa đăng ký.")
    khia_canh_che_tai: KhiaCanhCheTai = KHIA_CANH_CHE_TAI_FIELD


vi_pham_dang_ky_co_so_tro_giup = make_parent_leaf_template(
    name="vi_pham_dang_ky_co_so_tro_giup",
    description='Cơ sở trợ giúp hoạt động ngoài phạm vi hoặc chưa đăng ký Đ52 NĐ282.',
    params_schema=ViPhamDangKyCoSoTroGiupParams,
    parent_id="quy_dinh_dang_ky_co_so_tro_giup",
    router_field="tinh_trang_dang_ky",
    leaf_map=_LEAF_MAP,
    vphc_whitelist=_VPHC_WHITELIST,
    hs_whitelist=_HS_WHITELIST or None,
    dual_che_tai=False,
    hs_only=False,
)
