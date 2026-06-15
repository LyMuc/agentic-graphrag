"""Template — Truyền bá nội dung kích động bạo lực gia đình Đ49 NĐ282."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates.xu_phat_vi_pham._params_common import (
    KhiaCanhCheTai,
    KHIA_CANH_CHE_TAI_FIELD,
)
from adapter.cypher_templates.xu_phat_vi_pham._seed_factory import make_parent_leaf_template

_LEAF_MAP: dict[str, str] = {
    "thong_tin": "truyen_ba_thong_tin_kich_dong_bao_luc_gia_dinh",
        "tai_lieu": "truyen_ba_thong_tin_kich_dong_bao_luc_gia_dinh",
        "hinh_anh": "truyen_ba_thong_tin_kich_dong_bao_luc_gia_dinh",
        "am_thanh": "truyen_ba_thong_tin_kich_dong_bao_luc_gia_dinh",
        "khong_ro": "truyen_ba_thong_tin_kich_dong_bao_luc_gia_dinh"
}

_VPHC_WHITELIST = ['NghiDinh_282_2025_ND_CP_Dieu_49']
_HS_WHITELIST = []


class TruyenBaKichDongBaoLucParams(BaseModel):
    dang_noi_dung: Literal["thong_tin","tai_lieu","hinh_anh","am_thanh","khong_ro"] = Field(description="loại nội dung truyền bá kích động.")
    khia_canh_che_tai: KhiaCanhCheTai = KHIA_CANH_CHE_TAI_FIELD


truyen_ba_kich_dong_bao_luc = make_parent_leaf_template(
    name="truyen_ba_kich_dong_bao_luc",
    description='Truyền bá nội dung kích động bạo lực gia đình Đ49 NĐ282.',
    params_schema=TruyenBaKichDongBaoLucParams,
    parent_id="quy_dinh_truyen_ba_kich_dong_bao_luc",
    router_field="dang_noi_dung",
    leaf_map=_LEAF_MAP,
    vphc_whitelist=_VPHC_WHITELIST,
    hs_whitelist=_HS_WHITELIST or None,
    dual_che_tai=False,
    hs_only=False,
)
