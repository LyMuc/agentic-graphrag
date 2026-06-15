"""Template — Lợi dụng hoạt động phòng, chống bạo lực gia đình Đ51 NĐ282."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates.xu_phat_vi_pham._params_common import (
    KhiaCanhCheTai,
    KHIA_CANH_CHE_TAI_FIELD,
)
from adapter.cypher_templates.xu_phat_vi_pham._seed_factory import make_parent_leaf_template

_LEAF_MAP: dict[str, str] = {
    "doi_tien_thu_qua_gia": "doi_tien_sau_giup_do_hoac_thu_qua_gia_niem_yet",
        "bat_tra_chi_phi_tam_lanh": "yeu_cau_nan_nhan_tra_chi_phi_noi_tam_lanh",
        "loi_dung_hoan_canh_nan_nhan": "loi_dung_hoan_canh_nan_nhan_de_yeu_cau_trai_luat",
        "lap_co_so_co_loi_nhuan": "lap_co_so_tro_giup_de_hoat_dong_co_loi_nhuan",
        "loi_dung_hoat_dong_de_trai_luat": "loi_dung_hoat_dong_phong_chong_bao_luc_de_trai_luat",
        "tong_quat": ""
}

_VPHC_WHITELIST = ['NghiDinh_282_2025_ND_CP_Dieu_51']
_HS_WHITELIST = []


class LoiDungHoatDongPhongChongBaoLucParams(BaseModel):
    dang_hanh_vi: Literal["doi_tien_thu_qua_gia","bat_tra_chi_phi_tam_lanh","loi_dung_hoan_canh_nan_nhan","lap_co_so_co_loi_nhuan","loi_dung_hoat_dong_de_trai_luat","tong_quat"] = Field(description="lợi dụng hoạt động PCBLĐ.")
    khia_canh_che_tai: KhiaCanhCheTai = KHIA_CANH_CHE_TAI_FIELD


loi_dung_hoat_dong_phong_chong_bao_luc = make_parent_leaf_template(
    name="loi_dung_hoat_dong_phong_chong_bao_luc",
    description='Lợi dụng hoạt động phòng, chống bạo lực gia đình Đ51 NĐ282.',
    params_schema=LoiDungHoatDongPhongChongBaoLucParams,
    parent_id="quy_dinh_loi_dung_hoat_dong_phong_chong_bao_luc",
    router_field="dang_hanh_vi",
    leaf_map=_LEAF_MAP,
    vphc_whitelist=_VPHC_WHITELIST,
    hs_whitelist=_HS_WHITELIST or None,
    dual_che_tai=False,
    hs_only=False,
)
