"""Template — Xúc phạm danh dự, nhân phẩm hoặc phát tán bí mật gia đình Đ39 NĐ282."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates.xu_phat_vi_pham._params_common import (
    KhiaCanhCheTai,
    KHIA_CANH_CHE_TAI_FIELD,
)
from adapter.cypher_templates.xu_phat_vi_pham._seed_factory import make_parent_leaf_template

_LEAF_MAP: dict[str, str] = {
    "lang_ma_chiet_chi": "lang_ma_chiet_chi_xuc_pham_thanh_vien_gia_dinh",
        "phat_tan_bi_mat_de_xuc_pham": "phat_tan_bi_mat_doi_tu_de_xuc_pham",
        "tong_quat": ""
}

_VPHC_WHITELIST = ['NghiDinh_282_2025_ND_CP_Dieu_39']
_HS_WHITELIST = []


class XucPhamDanhDuBiMatParams(BaseModel):
    dang_hanh_vi: Literal["lang_ma_chiet_chi","phat_tan_bi_mat_de_xuc_pham","tong_quat"] = Field(description="lăng mạ; phát tán bí mật để xúc phạm.")
    khia_canh_che_tai: KhiaCanhCheTai = KHIA_CANH_CHE_TAI_FIELD


xuc_pham_danh_du_bi_mat = make_parent_leaf_template(
    name="xuc_pham_danh_du_bi_mat",
    description='Xúc phạm danh dự, nhân phẩm hoặc phát tán bí mật gia đình Đ39 NĐ282.',
    params_schema=XucPhamDanhDuBiMatParams,
    parent_id="quy_dinh_xuc_pham_danh_du_bi_mat",
    router_field="dang_hanh_vi",
    leaf_map=_LEAF_MAP,
    vphc_whitelist=_VPHC_WHITELIST,
    hs_whitelist=_HS_WHITELIST or None,
    dual_che_tai=False,
    hs_only=False,
)
