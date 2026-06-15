"""Template — Trốn tránh nghĩa vụ giám hộ hoặc lợi dụng quyền giám hộ."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates.xu_phat_vi_pham._params_common import (
    KhiaCanhCheTai,
    KHIA_CANH_CHE_TAI_FIELD,
)
from adapter.cypher_templates.xu_phat_vi_pham._seed_factory import make_parent_leaf_template

_LEAF_MAP: dict[str, str] = {
    "tron_tranh_nghia_vu": "tron_tranh_khong_thuc_hien_nghia_vu_giam_ho",
        "truc_loi": "loi_dung_giam_ho_de_truc_loi",
        "xam_pham_tinh_duc": "loi_dung_giam_ho_xam_pham_tinh_duc_boc_lot",
        "boc_lot_suc_lao_dong": "loi_dung_giam_ho_xam_pham_tinh_duc_boc_lot",
        "tong_quat": ""
}

_VPHC_WHITELIST = ['NghiDinh_82_2020_ND_CP_Dieu_61']
_HS_WHITELIST = []


class ViPhamGiamHoParams(BaseModel):
    dang_hanh_vi: Literal["tron_tranh_nghia_vu","truc_loi","xam_pham_tinh_duc","boc_lot_suc_lao_dong","tong_quat"] = Field(description="trốn giám hộ; lợi dụng giám hộ trục lợi/bóc lột.")
    khia_canh_che_tai: KhiaCanhCheTai = KHIA_CANH_CHE_TAI_FIELD


vi_pham_giam_ho = make_parent_leaf_template(
    name="vi_pham_giam_ho",
    description='Trốn tránh nghĩa vụ giám hộ hoặc lợi dụng quyền giám hộ.',
    params_schema=ViPhamGiamHoParams,
    parent_id="quy_dinh_vi_pham_giam_ho",
    router_field="dang_hanh_vi",
    leaf_map=_LEAF_MAP,
    vphc_whitelist=_VPHC_WHITELIST,
    hs_whitelist=_HS_WHITELIST or None,
    dual_che_tai=False,
    hs_only=False,
)
