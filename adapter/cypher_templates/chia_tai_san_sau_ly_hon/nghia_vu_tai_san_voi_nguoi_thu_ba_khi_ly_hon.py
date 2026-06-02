"""Template 3 — NGHĨA VỤ TÀI SẢN VỚI NGƯỜI THỨ BA KHI LY HÔN (Đ60).

Coverage feat_llm stt: 10,11,26,27.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.chia_tai_san_sau_ly_hon._common import (
    EXPAND_AND_TIMEFILTER_CYPHER,
    assemble_semantic_viz_all_seeds,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("loai_nghia_vu",)
_DIEU_60_WHITELIST = ["Luat_HNGD_2014_Dieu_60"]

_BASE_IDS = [
    "giai_quyet_quyen_nghia_vu_nguoi_thu_ba_khi_ly_hon",
    "quyen_nghia_vu_voi_nguoi_thu_ba_van_hieu_luc",
]
_TRANH_CHAP_IDS = ["co_tranh_chap_quyen_nghia_vu_tai_san"]


class NghiaVuTaiSanVoiNguoiThuBaParams(BaseModel):
    loai_nghia_vu: Literal[
        "no_chung",
        "vay_kinh_doanh",
        "vay_ca_nhan",
        "tranh_chap",
        "quyen_nghia_vu_nguoi_thu_ba",
        "khong_ro",
    ] = Field(
        default="khong_ro",
        description=(
            "Loại nghĩa vụ. Map: 'nợ chung'→no_chung; 'vay làm ăn/kinh doanh'→vay_kinh_doanh; "
            "'vay riêng/không sử dụng'→vay_ca_nhan; 'tranh chấp'→tranh_chap."
        ),
    )
    nguoi_thu_ba: Literal["ngan_hang", "chu_no", "nguoi_thu_ba", "khong_ro"] = Field(
        default="khong_ro",
        description="Map 'ngân hàng'→ngan_hang; 'chủ nợ'→chu_no.",
    )
    thoi_diem_no: Literal[
        "truoc_hon_nhan", "trong_hon_nhan", "sau_ly_hon", "khong_ro"
    ] = Field(default="khong_ro")
    muc_dich_no: Literal[
        "kinh_doanh", "nhu_cau_gia_dinh", "ca_nhan", "khong_ro"
    ] = Field(default="khong_ro")


_SEED_BLOCK = """
WITH $allowed_semantic_ids AS allowed, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (sn:ChiaTaiSanSauLyHon)
WHERE sn.id IN allowed AND sn.topic = 'chia_tai_san_sau_ly_hon'
  AND (sn:HanhVi OR sn:DieuKien OR sn:HauQua)

OPTIONAL MATCH (sn)-[:CAN_CU_TAI]->(luat_semantic)
WHERE luat_semantic IS NOT NULL

OPTIONAL MATCH (luat_whitelist:DieuLuat)
WHERE luat_whitelist.id IN wl

WITH collect(DISTINCT luat_semantic) + collect(DISTINCT luat_whitelist) AS all_seeds
UNWIND all_seeds AS n_goc
WITH DISTINCT n_goc
WHERE n_goc IS NOT NULL
"""


def _params_builder(params: NghiaVuTaiSanVoiNguoiThuBaParams) -> dict[str, Any]:
    ids = list(_BASE_IDS)
    if params.loai_nghia_vu in ("tranh_chap", "vay_ca_nhan", "khong_ro"):
        ids.extend(_TRANH_CHAP_IDS)
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "allowed_semantic_ids": list(dict.fromkeys(ids)),
        "whitelist_dieu_ids": _DIEU_60_WHITELIST if use_wl else [],
        # EXPERIMENT(no-whitelist): "whitelist_dieu_ids": _DIEU_60_WHITELIST,
        **params.model_dump(),
    }


nghia_vu_tai_san_voi_nguoi_thu_ba_khi_ly_hon = CypherTemplate(
    name="nghia_vu_tai_san_voi_nguoi_thu_ba_khi_ly_hon",
    description=(
        "Quyền, nghĩa vụ tài sản của vợ chồng với người thứ ba khi ly hôn (Đ60): "
        "nợ, vay ngân hàng, chủ nợ, hiệu lực sau ly hôn, tranh chấp quyền nghĩa vụ. "
        "Phù hợp khi câu hỏi có 'nợ', 'vay', 'trả nợ', 'ngân hàng', 'chủ nợ', "
        "'người thứ ba', 'nghĩa vụ tài sản'."
    ),
    params_schema=NghiaVuTaiSanVoiNguoiThuBaParams,
    cypher=_SEED_BLOCK.rstrip() + "\n\n" + EXPAND_AND_TIMEFILTER_CYPHER,
    viz_cypher=assemble_semantic_viz_all_seeds(_SEED_BLOCK),
    params_builder=_params_builder,
)
