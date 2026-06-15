"""Template — Bạo lực kinh tế: chiếm đoạt tài sản, kiểm soát thu nhập Đ44 NĐ282."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates.xu_phat_vi_pham._params_common import (
    KhiaCanhCheTai,
    KHIA_CANH_CHE_TAI_FIELD,
)
from adapter.cypher_templates.xu_phat_vi_pham._seed_factory import make_parent_leaf_template

_LEAF_MAP: dict[str, str] = {
    "chiem_doat_tai_san": "chiem_doat_tai_san_gia_dinh",
        "huy_hoai_tai_san": "huy_hoai_tai_san_gia_dinh",
        "ep_lao_dong_qua_suc": "cuong_ep_thanh_vien_lao_dong_qua_suc",
        "ep_dong_gop_qua_kha_nang": "cuong_ep_dong_gop_tai_chinh_qua_kha_nang",
        "kiem_soat_tai_san_thu_nhap": "kiem_soat_tai_san_thu_nhap_tao_le_thuoc",
        "tong_quat": ""
}

_VPHC_WHITELIST = ['NghiDinh_282_2025_ND_CP_Dieu_44']
_HS_WHITELIST = []


class BaoLucKinhTeParams(BaseModel):
    dang_hanh_vi: Literal["chiem_doat_tai_san","huy_hoai_tai_san","ep_lao_dong_qua_suc","ep_dong_gop_qua_kha_nang","kiem_soat_tai_san_thu_nhap","tong_quat"] = Field(description="chiếm đoạt tài sản; kiểm soát thu nhập.")
    loai_tai_san: Literal["tai_san_chung","tai_san_rieng","thu_nhap","khong_ro"] = Field(description="loại tài sản bị xâm hại.")
    khia_canh_che_tai: KhiaCanhCheTai = KHIA_CANH_CHE_TAI_FIELD


bao_luc_kinh_te = make_parent_leaf_template(
    name="bao_luc_kinh_te",
    description='Bạo lực kinh tế: chiếm đoạt tài sản, kiểm soát thu nhập Đ44 NĐ282.',
    params_schema=BaoLucKinhTeParams,
    parent_id="quy_dinh_bao_luc_kinh_te",
    router_field="dang_hanh_vi",
    leaf_map=_LEAF_MAP,
    vphc_whitelist=_VPHC_WHITELIST,
    hs_whitelist=_HS_WHITELIST or None,
    dual_che_tai=False,
    hs_only=False,
)
