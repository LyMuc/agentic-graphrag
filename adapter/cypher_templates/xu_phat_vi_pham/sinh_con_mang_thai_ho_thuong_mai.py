"""Template — Sinh con hỗ trợ thương mại, sinh sản vô tính, mang thai hộ và tổ chức ma"""
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
    "sinh_con_ho_tro_thuong_mai": "sinh_con_ho_tro_vi_muc_dich_thuong_mai",
        "sinh_san_vo_tinh": "thuc_hien_sinh_san_vo_tinh",
        "lua_chon_gioi_tinh_thai_nhi": "lua_chon_gioi_tinh_thai_nhi",
        "mang_thai_ho_thuong_mai": "mang_thai_ho_vi_muc_dich_thuong_mai",
        "to_chuc_mang_thai_ho_thuong_mai": "to_chuc_mang_thai_ho_vi_muc_dich_thuong_mai",
        "tong_quat": ""
}

_VPHC_WHITELIST = ['NghiDinh_82_2020_ND_CP_Dieu_60']
_HS_WHITELIST = ['BoLuat_HinhSu_2015_Dieu_187']


class SinhConMangThaiHoThuongMaiParams(BaseModel):
    dang_hanh_vi: Literal["sinh_con_ho_tro_thuong_mai","sinh_san_vo_tinh","lua_chon_gioi_tinh_thai_nhi","mang_thai_ho_thuong_mai","to_chuc_mang_thai_ho_thuong_mai","tong_quat"] = Field(description="mang thai hộ lấy tiền; chọn giới tính thai nhi; tổ chức mang thai hộ thương mại.")
    loai_che_tai: LoaiCheTai = LOAI_CHE_TAI_FIELD
    khia_canh_che_tai: KhiaCanhCheTai = KHIA_CANH_CHE_TAI_FIELD


sinh_con_mang_thai_ho_thuong_mai = make_parent_leaf_template(
    name="sinh_con_mang_thai_ho_thuong_mai",
    description='Sinh con hỗ trợ thương mại, sinh sản vô tính, mang thai hộ và tổ chức mang thai hộ thương mại.',
    params_schema=SinhConMangThaiHoThuongMaiParams,
    parent_id="quy_dinh_sinh_con_mang_thai_ho_thuong_mai",
    router_field="dang_hanh_vi",
    leaf_map=_LEAF_MAP,
    vphc_whitelist=_VPHC_WHITELIST,
    hs_whitelist=_HS_WHITELIST or None,
    dual_che_tai=True,
    hs_only=False,
)
