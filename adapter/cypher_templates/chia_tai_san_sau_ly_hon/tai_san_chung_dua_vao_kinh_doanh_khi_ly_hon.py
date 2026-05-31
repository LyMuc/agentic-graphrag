"""Template 6 — TÀI SẢN CHUNG ĐƯA VÀO KINH DOANH KHI LY HÔN (Đ64).

Coverage feat_llm stt: 19,20.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.chia_tai_san_sau_ly_hon._common import (
    EXPAND_AND_TIMEFILTER_CYPHER,
)

_SEMANTIC_IDS = [
    "chia_tai_san_chung_dua_vao_kinh_doanh",
    "nhan_tai_san_kinh_doanh_va_thanh_toan_gia_tri",
]


class TaiSanChungDuaVaoKinhDoanhParams(BaseModel):
    nguoi_dang_kinh_doanh: Literal["vo", "chong", "ca_hai", "khong_ro"] = Field(
        default="khong_ro"
    )
    tai_san_chung_lien_quan_kinh_doanh: Literal["co", "khong_ro"] = Field(
        default="khong_ro",
        description="Map 'đưa vào kinh doanh/góp vốn/làm ăn'→co.",
    )
    phap_luat_kinh_doanh_khac: Literal["co", "khong", "khong_ro"] = Field(
        default="khong_ro"
    )


_SEED_BLOCK = """
WITH $allowed_semantic_ids AS allowed, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (sn:ChiaTaiSanSauLyHon)
WHERE sn.id IN allowed AND sn.topic = 'chia_tai_san_sau_ly_hon'
  AND (sn:HanhVi OR sn:HauQua)

OPTIONAL MATCH (sn)-[:CAN_CU_TAI]->(luat_semantic)
WHERE luat_semantic IS NOT NULL

OPTIONAL MATCH (luat_whitelist:DieuLuat)
WHERE luat_whitelist.id IN wl

WITH collect(DISTINCT luat_semantic) + collect(DISTINCT luat_whitelist) AS all_seeds
UNWIND all_seeds AS n_goc
WITH DISTINCT n_goc
WHERE n_goc IS NOT NULL
"""


def _params_builder(params: TaiSanChungDuaVaoKinhDoanhParams) -> dict[str, Any]:
    return {
        "allowed_semantic_ids": _SEMANTIC_IDS,
        "whitelist_dieu_ids": ["Luat_HNGD_2014_Dieu_64"],
        **params.model_dump(),
    }


tai_san_chung_dua_vao_kinh_doanh_khi_ly_hon = CypherTemplate(
    name="tai_san_chung_dua_vao_kinh_doanh_khi_ly_hon",
    description=(
        "Tài sản chung của vợ chồng đã đưa vào hoạt động kinh doanh khi ly hôn "
        "(Đ64): bên đang kinh doanh nhận tài sản và thanh toán giá trị cho bên kia. "
        "Phù hợp khi có 'đưa vào kinh doanh', 'tài sản kinh doanh', 'góp vốn', "
        "'làm ăn kinh doanh' và hỏi chia tài sản khi ly hôn."
    ),
    params_schema=TaiSanChungDuaVaoKinhDoanhParams,
    cypher=_SEED_BLOCK.rstrip() + "\n\n" + EXPAND_AND_TIMEFILTER_CYPHER,
    params_builder=_params_builder,
)
