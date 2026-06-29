"""Template — Vi phạm quyết định cấm tiếp xúc Đ53 NĐ282."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from server.infrastructure.neo4j.cypher_templates.xu_phat_vi_pham._params_common import (
    KhiaCanhCheTai,
    KHIA_CANH_CHE_TAI_FIELD,
)
from server.infrastructure.neo4j.cypher_templates.xu_phat_vi_pham._seed_factory import make_parent_leaf_template

_LEAF_MAP: dict[str, str] = {
    "den_gan_trong_100m": "co_tinh_den_gan_nguoi_bi_cam_tiep_xuc",
        "dung_dien_thoai_email_cong_cu_de_bao_luc": "dung_phuong_tien_de_bao_luc_nguoi_bi_cam_tiep_xuc",
        "tong_quat": ""
}

_VPHC_WHITELIST = ['NghiDinh_282_2025_ND_CP_Dieu_53']
_HS_WHITELIST = []


class ViPhamCamTiepXucParams(BaseModel):
    dang_vi_pham: Literal["den_gan_trong_100m","dung_dien_thoai_email_cong_cu_de_bao_luc","tong_quat"] = Field(description="đến gần 100m; liên lạc đe dọa khi bị cấm tiếp xúc.")
    khia_canh_che_tai: KhiaCanhCheTai = KHIA_CANH_CHE_TAI_FIELD


vi_pham_cam_tiep_xuc = make_parent_leaf_template(
    name="vi_pham_cam_tiep_xuc",
    description='Vi phạm quyết định cấm tiếp xúc Đ53 NĐ282.',
    params_schema=ViPhamCamTiepXucParams,
    parent_id="quy_dinh_vi_pham_cam_tiep_xuc",
    router_field="dang_vi_pham",
    leaf_map=_LEAF_MAP,
    vphc_whitelist=_VPHC_WHITELIST,
    hs_whitelist=_HS_WHITELIST or None,
    dual_che_tai=False,
    hs_only=False,
)
