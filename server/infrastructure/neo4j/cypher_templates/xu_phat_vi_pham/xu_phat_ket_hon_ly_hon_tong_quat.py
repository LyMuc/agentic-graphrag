"""Template — Câu hỏi tổng quát về kết hôn trái pháp luật, vi phạm kết hôn/ly hôn hoặc"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from server.infrastructure.neo4j.cypher_templates.xu_phat_vi_pham._params_common import (
    LoaiCheTai,
    LOAI_CHE_TAI_FIELD,
    KhiaCanhCheTai,
    KHIA_CANH_CHE_TAI_FIELD,
)
from server.infrastructure.neo4j.cypher_templates.xu_phat_vi_pham._seed_factory import make_parent_leaf_template

_LEAF_MAP: dict[str, str] = {
    "ket_hon_trai_phap_luat": "ket_hon_khi_dang_co_vo_chong",
        "vi_pham_ket_hon_ly_hon": "can_tro_ket_hon_hoac_ly_hon",
        "tong_quat": ""
}

_VPHC_WHITELIST = ['NghiDinh_82_2020_ND_CP_Dieu_59', 'Luat_HNGD_2014_Dieu_3_Khoan_6']
_HS_WHITELIST = ['BoLuat_HinhSu_2015_Dieu_182']


class XuPhatKetHonLyHonTongQuatParams(BaseModel):
    pham_vi: Literal["ket_hon_trai_phap_luat","vi_pham_ket_hon_ly_hon","tong_quat"] = Field(description="kết hôn trái pháp luật/hợp đồng hôn nhân → ket_hon_trai_phap_luat; vi phạm kết hôn ly hôn → vi_pham_ket_hon_ly_hon.")
    loai_che_tai: LoaiCheTai = LOAI_CHE_TAI_FIELD
    khia_canh_che_tai: KhiaCanhCheTai = KHIA_CANH_CHE_TAI_FIELD


xu_phat_ket_hon_ly_hon_tong_quat = make_parent_leaf_template(
    name="xu_phat_ket_hon_ly_hon_tong_quat",
    description='Câu hỏi tổng quát về kết hôn trái pháp luật, vi phạm kết hôn/ly hôn hoặc hợp đồng hôn nhân trái pháp luật khi chưa đủ dữ kiện chọn template hẹp.',
    params_schema=XuPhatKetHonLyHonTongQuatParams,
    parent_id="quy_dinh_ket_hon_ly_hon_tong_quat",
    router_field="pham_vi",
    leaf_map=_LEAF_MAP,
    vphc_whitelist=_VPHC_WHITELIST,
    hs_whitelist=_HS_WHITELIST or None,
    dual_che_tai=True,
    hs_only=False,
)
