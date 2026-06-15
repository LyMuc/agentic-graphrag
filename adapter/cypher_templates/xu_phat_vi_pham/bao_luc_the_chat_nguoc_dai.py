"""Template — Bạo lực thể chất, hành hạ, ngược đãi. VPHC Đ37 và TNHS Đ185."""
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
    "de_doa": "de_doa_xam_hai_suc_khoe_tinh_mang_thanh_vien_gia_dinh",
        "danh_dap": "danh_dap_xam_hai_suc_khoe_thanh_vien_gia_dinh",
        "hanh_ha_nguoc_dai": "hanh_ha_nguoc_dai_thanh_vien_gia_dinh",
        "dung_cong_cu_gay_thuong_tich": "dung_cong_cu_gay_thuong_tich_thanh_vien_gia_dinh",
        "khong_cap_cuu_cham_soc": "khong_cap_cuu_cham_soc_nan_nhan_bao_luc",
        "tong_quat": ""
}

_VPHC_WHITELIST = ['NghiDinh_282_2025_ND_CP_Dieu_37']
_HS_WHITELIST = ['BoLuat_HinhSu_2015_Dieu_185']


class BaoLucTheChatNguocDaiParams(BaseModel):
    dang_hanh_vi: Literal["de_doa","danh_dap","hanh_ha_nguoc_dai","dung_cong_cu_gay_thuong_tich","khong_cap_cuu_cham_soc","tong_quat"] = Field(description="đánh đập; ngược đại; không cấp cứu.")
    doi_tuong_dac_biet: Literal["duoi_16_tuoi","phu_nu_mang_thai","nguoi_gia_yeu","nguoi_khuyet_tat_nang","nguoi_om_dau","khong_ro"] = Field(description="Đối tượng yếu thế cho Đ185.")
    loai_che_tai: LoaiCheTai = LOAI_CHE_TAI_FIELD
    khia_canh_che_tai: KhiaCanhCheTai = KHIA_CANH_CHE_TAI_FIELD


bao_luc_the_chat_nguoc_dai = make_parent_leaf_template(
    name="bao_luc_the_chat_nguoc_dai",
    description='Bạo lực thể chất, hành hạ, ngược đãi. VPHC Đ37 và TNHS Đ185.',
    params_schema=BaoLucTheChatNguocDaiParams,
    parent_id="quy_dinh_bao_luc_the_chat_nguoc_dai",
    router_field="dang_hanh_vi",
    leaf_map=_LEAF_MAP,
    vphc_whitelist=_VPHC_WHITELIST,
    hs_whitelist=_HS_WHITELIST or None,
    dual_che_tai=True,
    hs_only=False,
)
