"""Template — Kết hôn/ly hôn giả tạo để nhập cư, nhập quốc tịch hoặc trốn nghĩa vụ tài"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates.xu_phat_vi_pham._params_common import (
    KhiaCanhCheTai,
    KHIA_CANH_CHE_TAI_FIELD,
)
from adapter.cypher_templates.xu_phat_vi_pham._seed_factory import make_parent_leaf_template

_LEAF_MAP: dict[str, str] = {
    "ket_hon_gia_tao": "ket_hon_gia_tao_de_dat_muc_dich_khac",
        "ly_hon_gia_tao": "ly_hon_gia_tao_de_tron_nghia_vu",
        "khong_ro": ""
}

_VPHC_WHITELIST = ['NghiDinh_82_2020_ND_CP_Dieu_59_Khoan_2_Diem_d']
_HS_WHITELIST = []


class KetHonLyHonGiaTaoParams(BaseModel):
    dang_gia_tao: Literal["ket_hon_gia_tao","ly_hon_gia_tao","khong_ro"] = Field(description="kết hôn giả/ly hôn giả.")
    muc_dich: Literal["xuat_nhap_canh_cu_tru","nhap_quoc_tich","huong_uu_dai","tron_nghia_vu_tai_san","vi_pham_dan_so","muc_dich_khac","khong_ro"] = Field(description="nhập quốc tịch; trốn nghĩa vụ tài sản.")
    khia_canh_che_tai: KhiaCanhCheTai = KHIA_CANH_CHE_TAI_FIELD


ket_hon_ly_hon_gia_tao = make_parent_leaf_template(
    name="ket_hon_ly_hon_gia_tao",
    description='Kết hôn/ly hôn giả tạo để nhập cư, nhập quốc tịch hoặc trốn nghĩa vụ tài sản.',
    params_schema=KetHonLyHonGiaTaoParams,
    parent_id="quy_dinh_ket_hon_ly_hon_gia_tao",
    router_field="dang_gia_tao",
    leaf_map=_LEAF_MAP,
    vphc_whitelist=_VPHC_WHITELIST,
    hs_whitelist=_HS_WHITELIST or None,
    dual_che_tai=False,
    hs_only=False,
)
