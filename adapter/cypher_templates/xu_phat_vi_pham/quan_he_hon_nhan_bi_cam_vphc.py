"""Template — Kết hôn/chung sống trong quan hệ bị cấm theo Đ59 NĐ82 (VPHC). Không dùng"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates.xu_phat_vi_pham._params_common import (
    KhiaCanhCheTai,
    KHIA_CANH_CHE_TAI_FIELD,
)
from adapter.cypher_templates.xu_phat_vi_pham._seed_factory import make_parent_leaf_template

_LEAF_MAP: dict[str, str] = {
    "cung_dong_mau_truc_he": "ket_hon_chung_song_cung_dong_mau_truc_he_hoac_ba_doi",
        "trong_pham_vi_ba_doi": "ket_hon_chung_song_cung_dong_mau_truc_he_hoac_ba_doi",
        "cha_me_nuoi_con_nuoi": "ket_hon_chung_song_cha_me_nuoi_con_nuoi",
        "quan_he_thong_gia_nuoi_duong_cu": "ket_hon_chung_song_quan_he_thong_gia_nuoi_duong_cu",
        "khong_ro": ""
}

_VPHC_WHITELIST = ['NghiDinh_82_2020_ND_CP_Dieu_59_Khoan_2_Diem_a']
_HS_WHITELIST = []


class QuanHeHonNhanBiCamVphcParams(BaseModel):
    moi_quan_he: Literal["cung_dong_mau_truc_he","trong_pham_vi_ba_doi","cha_me_nuoi_con_nuoi","quan_he_thong_gia_nuoi_duong_cu","khong_ro"] = Field(description="ba đời/cận huyết → trong_pham_vi_ba_doi; cha nuôi → cha_me_nuoi_con_nuoi.")
    dang_quan_he: Literal["ket_hon","chung_song_nhu_vo_chong","khong_ro"] = Field(description="kết hôn hoặc chung sống.")
    khia_canh_che_tai: KhiaCanhCheTai = KHIA_CANH_CHE_TAI_FIELD


quan_he_hon_nhan_bi_cam_vphc = make_parent_leaf_template(
    name="quan_he_hon_nhan_bi_cam_vphc",
    description='Kết hôn/chung sống trong quan hệ bị cấm theo Đ59 NĐ82 (VPHC). Không dùng cho tội loạn luân.',
    params_schema=QuanHeHonNhanBiCamVphcParams,
    parent_id="quy_dinh_quan_he_hon_nhan_bi_cam_vphc",
    router_field="moi_quan_he",
    leaf_map=_LEAF_MAP,
    vphc_whitelist=_VPHC_WHITELIST,
    hs_whitelist=_HS_WHITELIST or None,
    dual_che_tai=False,
    hs_only=False,
)
