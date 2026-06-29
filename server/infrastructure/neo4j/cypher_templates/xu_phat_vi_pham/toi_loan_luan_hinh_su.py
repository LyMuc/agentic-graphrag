"""Template — Tội loạn luân Đ184 BLHS. Không suy ra từ kết hôn trong phạm vi ba đời."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from server.infrastructure.neo4j.cypher_templates.xu_phat_vi_pham._params_common import (
    KhiaCanhCheTai,
    KHIA_CANH_CHE_TAI_FIELD,
)
from server.infrastructure.neo4j.cypher_templates.xu_phat_vi_pham._seed_factory import make_parent_leaf_template

_LEAF_MAP: dict[str, str] = {
    "cung_dong_mau_truc_he": "giao_cau_voi_nguoi_cung_dong_mau_truc_he_hoac_anh_chi_em",
        "anh_chi_em_cung_cha_me": "giao_cau_voi_nguoi_cung_dong_mau_truc_he_hoac_anh_chi_em",
        "can_huyet_khong_ro": "giao_cau_voi_nguoi_cung_dong_mau_truc_he_hoac_anh_chi_em"
}

_VPHC_WHITELIST = []
_HS_WHITELIST = ['BoLuat_HinhSu_2015_Dieu_184']


class ToiLoanLuanHinhSuParams(BaseModel):
    moi_quan_he: Literal["cung_dong_mau_truc_he","anh_chi_em_cung_cha_me","anh_chi_em_cung_cha_khac_me","anh_chi_em_cung_me_khac_cha","can_huyet_khong_ro"] = Field(description="Quan hệ theo Đ184 BLHS.")
    co_hanh_vi_giao_cau: Literal["co","khong","khong_ro"] = Field(description="loạn luân/giao cấu → co; kết hôn cận huyết mơ hồ → khong_ro.")
    khia_canh_che_tai: KhiaCanhCheTai = KHIA_CANH_CHE_TAI_FIELD


toi_loan_luan_hinh_su = make_parent_leaf_template(
    name="toi_loan_luan_hinh_su",
    description='Tội loạn luân Đ184 BLHS. Không suy ra từ kết hôn trong phạm vi ba đời.',
    params_schema=ToiLoanLuanHinhSuParams,
    parent_id="quy_dinh_toi_loan_luan",
    router_field="moi_quan_he",
    leaf_map=_LEAF_MAP,
    vphc_whitelist=_VPHC_WHITELIST,
    hs_whitelist=_HS_WHITELIST or None,
    dual_che_tai=False,
    hs_only=True,
)
