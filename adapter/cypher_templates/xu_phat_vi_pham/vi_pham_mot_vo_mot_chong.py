"""Template — Ngoại tình, vi phạm một vợ một chồng. Tách phạt hành chính Đ59 và TNHS Đ"""
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
    "ket_hon_voi_nguoi_khac": "ket_hon_khi_dang_co_vo_chong",
        "chung_song_khi_dang_co_vo_chong": "chung_song_voi_nguoi_khac_khi_dang_co_vo_chong",
        "chung_song_voi_nguoi_biet_ro": "chung_song_voi_nguoi_biet_ro_dang_co_vo_chong",
        "ngoai_tinh_khong_ro": "",
        "tong_quat": ""
}

_VPHC_WHITELIST = ['NghiDinh_82_2020_ND_CP_Dieu_59_Khoan_1']
_HS_WHITELIST = ['BoLuat_HinhSu_2015_Dieu_182']


class ViPhamMotVoMotChongParams(BaseModel):
    dang_hanh_vi: Literal["ket_hon_voi_nguoi_khac","chung_song_khi_dang_co_vo_chong","chung_song_voi_nguoi_biet_ro","ngoai_tinh_khong_ro","tong_quat"] = Field(description="ngoại tình → ngoai_tinh_khong_ro; sống như vợ chồng → chung_song_*.")
    hau_qua_hinh_su: Literal["dan_den_ly_hon","lam_tu_sat","khong_chap_hanh_quyet_dinh_toa","da_bi_xu_phat_vphc","khong_ro"] = Field(description="Hậu quả định khung TNHS Đ182.")
    loai_che_tai: LoaiCheTai = LOAI_CHE_TAI_FIELD
    khia_canh_che_tai: KhiaCanhCheTai = KHIA_CANH_CHE_TAI_FIELD


vi_pham_mot_vo_mot_chong = make_parent_leaf_template(
    name="vi_pham_mot_vo_mot_chong",
    description='Ngoại tình, vi phạm một vợ một chồng. Tách phạt hành chính Đ59 và TNHS Đ182; ngoại tình đơn thuần không đủ kết luận hình sự.',
    params_schema=ViPhamMotVoMotChongParams,
    parent_id="quy_dinh_mot_vo_mot_chong",
    router_field="dang_hanh_vi",
    leaf_map=_LEAF_MAP,
    vphc_whitelist=_VPHC_WHITELIST,
    hs_whitelist=_HS_WHITELIST or None,
    dual_che_tai=True,
    hs_only=False,
)
