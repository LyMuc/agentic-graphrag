"""Template — Tiết lộ thông tin nạn nhân/người báo tin; không công khai bảng giá Đ50 N"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from server.infrastructure.neo4j.cypher_templates.xu_phat_vi_pham._params_common import (
    KhiaCanhCheTai,
    KHIA_CANH_CHE_TAI_FIELD,
)
from server.infrastructure.neo4j.cypher_templates.xu_phat_vi_pham._seed_factory import make_parent_leaf_template

_LEAF_MAP: dict[str, str] = {
    "tiet_lo_noi_tam_lanh": "tiet_lo_noi_tam_lanh_cho_nguoi_bao_luc",
        "tiet_lo_nguoi_bao_tin": "tiet_lo_thong_tin_nguoi_bao_tin_khong_dong_y",
        "khong_cong_khai_bang_gia": "khong_cong_khai_bang_gia_dich_vu_tro_giup",
        "tong_quat": ""
}

_VPHC_WHITELIST = ['NghiDinh_282_2025_ND_CP_Dieu_50']
_HS_WHITELIST = []


class TietLoThongTinVaBangGiaParams(BaseModel):
    dang_hanh_vi: Literal["tiet_lo_noi_tam_lanh","tiet_lo_nguoi_bao_tin","khong_cong_khai_bang_gia","tong_quat"] = Field(description="tiết lộ nơi tạm lánh; người báo tin; bảng giá.")
    khia_canh_che_tai: KhiaCanhCheTai = KHIA_CANH_CHE_TAI_FIELD


tiet_lo_thong_tin_va_bang_gia = make_parent_leaf_template(
    name="tiet_lo_thong_tin_va_bang_gia",
    description='Tiết lộ thông tin nạn nhân/người báo tin; không công khai bảng giá Đ50 NĐ282.',
    params_schema=TietLoThongTinVaBangGiaParams,
    parent_id="quy_dinh_tiet_lo_thong_tin_va_bang_gia",
    router_field="dang_hanh_vi",
    leaf_map=_LEAF_MAP,
    vphc_whitelist=_VPHC_WHITELIST,
    hs_whitelist=_HS_WHITELIST or None,
    dual_che_tai=False,
    hs_only=False,
)
