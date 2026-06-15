"""Template — Vi phạm nghĩa vụ ngăn chặn, báo tin, xử lý tin báo bạo lực Đ48 NĐ282."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates.xu_phat_vi_pham._params_common import (
    KhiaCanhCheTai,
    KHIA_CANH_CHE_TAI_FIELD,
)
from adapter.cypher_templates.xu_phat_vi_pham._seed_factory import make_parent_leaf_template

_LEAF_MAP: dict[str, str] = {
    "khong_ngan_chan": "biet_bao_luc_co_dieu_kien_nhung_khong_ngan_chan",
        "khong_bao_tin": "biet_bao_luc_nhung_khong_bao_tin",
        "dung_tung_bao_che": "dung_tung_bao_che_bao_luc_gia_dinh",
        "khong_truc_tong_dai": "khong_bo_tri_truc_tong_dai_bao_luc_24_7",
        "vi_pham_quy_trinh_tong_dai": "vi_pham_quy_trinh_tiep_nhan_xu_ly_tin_bao_tong_dai",
        "can_tro_xu_ly": "can_tro_xu_ly_bao_luc_gia_dinh",
        "khong_xu_ly_xu_ly_sai": "khong_xu_ly_hoac_xu_ly_sai_bao_luc_gia_dinh",
        "khong_chap_hanh_bien_phap_cong_dong": "khong_chap_hanh_gop_y_hoac_phuc_vu_cong_dong",
        "tong_quat": ""
}

_VPHC_WHITELIST = ['NghiDinh_282_2025_ND_CP_Dieu_48']
_HS_WHITELIST = []


class ViPhamNganChanBaoTinXuLyParams(BaseModel):
    dang_hanh_vi: Literal["khong_ngan_chan","khong_bao_tin","dung_tung_bao_che","khong_truc_tong_dai","vi_pham_quy_trinh_tong_dai","can_tro_xu_ly","khong_xu_ly_xu_ly_sai","khong_chap_hanh_bien_phap_cong_dong","tong_quat"] = Field(description="không báo tin; cơ quan không xử lý.")
    khia_canh_che_tai: KhiaCanhCheTai = KHIA_CANH_CHE_TAI_FIELD


vi_pham_ngan_chan_bao_tin_xu_ly = make_parent_leaf_template(
    name="vi_pham_ngan_chan_bao_tin_xu_ly",
    description='Vi phạm nghĩa vụ ngăn chặn, báo tin, xử lý tin báo bạo lực Đ48 NĐ282.',
    params_schema=ViPhamNganChanBaoTinXuLyParams,
    parent_id="quy_dinh_ngan_chan_bao_tin_xu_ly",
    router_field="dang_hanh_vi",
    leaf_map=_LEAF_MAP,
    vphc_whitelist=_VPHC_WHITELIST,
    hs_whitelist=_HS_WHITELIST or None,
    dual_che_tai=False,
    hs_only=False,
)
