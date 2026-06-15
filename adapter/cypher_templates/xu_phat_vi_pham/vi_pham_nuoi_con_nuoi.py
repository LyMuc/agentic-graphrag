"""Template — Vi phạm quy định về nuôi con nuôi Đ62 NĐ82."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates.xu_phat_vi_pham._params_common import (
    KhiaCanhCheTai,
    KHIA_CANH_CHE_TAI_FIELD,
)
from adapter.cypher_templates.xu_phat_vi_pham._seed_factory import make_parent_leaf_template

_LEAF_MAP: dict[str, str] = {
    "khai_sai": "khai_sai_de_dang_ky_nuoi_con_nuoi",
        "phan_biet_con_de_con_nuoi": "phan_biet_doi_xu_con_de_con_nuoi",
        "khong_bao_cao": "khong_bao_cao_tinh_hinh_con_nuoi_trong_nuoc",
        "tay_xoa_giay_to": "tay_xoa_giay_to_nuoi_con_nuoi",
        "loi_dung_dan_so": "loi_dung_cho_con_nuoi_vi_pham_dan_so",
        "loi_dung_huong_uu_dai": "loi_dung_lam_con_nuoi_de_huong_uu_dai",
        "ep_buoc_dong_y": "mua_chuoc_ep_buoc_de_co_dong_y_cho_con_nuoi",
        "truc_loi": "loi_dung_cho_nhan_gioi_thieu_con_nuoi_de_truc_loi",
        "boc_lot_suc_lao_dong": "loi_dung_nhan_con_nuoi_de_boc_lot",
        "tong_quat": ""
}

_VPHC_WHITELIST = ['NghiDinh_82_2020_ND_CP_Dieu_62']
_HS_WHITELIST = []


class ViPhamNuoiConNuoiParams(BaseModel):
    dang_hanh_vi: Literal["khai_sai","phan_biet_con_de_con_nuoi","khong_bao_cao","tay_xoa_giay_to","loi_dung_dan_so","loi_dung_huong_uu_dai","ep_buoc_dong_y","truc_loi","boc_lot_suc_lao_dong","tong_quat"] = Field(description="Vi phạm nuôi con nuôi Đ62 NĐ82.")
    khia_canh_che_tai: KhiaCanhCheTai = KHIA_CANH_CHE_TAI_FIELD


vi_pham_nuoi_con_nuoi = make_parent_leaf_template(
    name="vi_pham_nuoi_con_nuoi",
    description='Vi phạm quy định về nuôi con nuôi Đ62 NĐ82.',
    params_schema=ViPhamNuoiConNuoiParams,
    parent_id="quy_dinh_vi_pham_nuoi_con_nuoi",
    router_field="dang_hanh_vi",
    leaf_map=_LEAF_MAP,
    vphc_whitelist=_VPHC_WHITELIST,
    hs_whitelist=_HS_WHITELIST or None,
    dual_che_tai=False,
    hs_only=False,
)
