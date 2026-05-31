"""Template 5 — TRƯỜNG HỢP NHÀ Ở GIA ĐÌNH VÀ LƯU CƯ (Đ61, Đ63).

Coverage feat_llm stt: 12,18.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.chia_tai_san_sau_ly_hon._common import (
    EXPAND_AND_TIMEFILTER_CYPHER,
)

_D61_IDS = [
    "chia_tai_san_song_chung_voi_gia_dinh",
    "tai_san_vo_chong_trong_khoi_gia_dinh_khong_xac_dinh_duoc",
    "tai_san_vo_chong_trong_khoi_gia_dinh_xac_dinh_duoc_theo_phan",
]
_D63_IDS = [
    "luu_cu_sau_ly_hon",
    "nha_o_rieng_da_dua_vao_su_dung_chung",
    "kho_khan_ve_cho_o",
    "thoi_han_luu_cu_06_thang",
]


class TruongHopNhaOGiaDinhVaLuuCuParams(BaseModel):
    loai_truong_hop: Literal[
        "song_chung_voi_gia_dinh", "luu_cu_nha_rieng", "tat_ca"
    ] = Field(
        description=(
            "Map 'sống chung với gia đình/khối tài sản chung gia đình'→"
            "song_chung_voi_gia_dinh; 'ở lại nhà riêng/lưu cư/khó khăn chỗ ở'→"
            "luu_cu_nha_rieng."
        )
    )
    xac_dinh_duoc_phan_tai_san: Literal["co", "khong", "khong_ro"] = Field(
        default="khong_ro",
        description="Đ61: 'không xác định được'→khong; 'xác định theo phần'→co.",
    )
    kho_khan_cho_o: Literal["co", "khong", "khong_ro"] = Field(default="khong_ro")
    thoa_thuan_khac: Literal["co", "khong", "khong_ro"] = Field(default="khong_ro")


_SEED_BLOCK = """
WITH $allowed_semantic_ids AS allowed, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (sn:ChiaTaiSanSauLyHon)
WHERE sn.id IN allowed AND sn.topic = 'chia_tai_san_sau_ly_hon'
  AND (sn:HanhVi OR sn:DieuKien OR sn:HauQua OR sn:LoaiTaiSan)

OPTIONAL MATCH (sn)-[:CAN_CU_TAI]->(luat_semantic)
WHERE luat_semantic IS NOT NULL

OPTIONAL MATCH (luat_whitelist:DieuLuat)
WHERE luat_whitelist.id IN wl

WITH collect(DISTINCT luat_semantic) + collect(DISTINCT luat_whitelist) AS all_seeds
UNWIND all_seeds AS n_goc
WITH DISTINCT n_goc
WHERE n_goc IS NOT NULL
"""


def _params_builder(params: TruongHopNhaOGiaDinhVaLuuCuParams) -> dict[str, Any]:
    ids: list[str] = []
    wl: list[str] = []

    if params.loai_truong_hop in ("song_chung_voi_gia_dinh", "tat_ca"):
        ids.extend(_D61_IDS)
        wl.append("Luat_HNGD_2014_Dieu_61")
        if params.xac_dinh_duoc_phan_tai_san == "khong":
            ids.append("tai_san_vo_chong_trong_khoi_gia_dinh_khong_xac_dinh_duoc")
        elif params.xac_dinh_duoc_phan_tai_san == "co":
            ids.append("tai_san_vo_chong_trong_khoi_gia_dinh_xac_dinh_duoc_theo_phan")

    if params.loai_truong_hop in ("luu_cu_nha_rieng", "tat_ca"):
        ids.extend(_D63_IDS)
        wl.append("Luat_HNGD_2014_Dieu_63")
        if params.kho_khan_cho_o == "co":
            ids.append("kho_khan_ve_cho_o")

    return {
        "allowed_semantic_ids": list(dict.fromkeys(ids)),
        "whitelist_dieu_ids": list(dict.fromkeys(wl)),
        **params.model_dump(),
    }


truong_hop_nha_o_gia_dinh_va_luu_cu = CypherTemplate(
    name="truong_hop_nha_o_gia_dinh_va_luu_cu",
    description=(
        "Hai tình huống đặc biệt sau ly hôn: (1) chia tài sản khi vợ chồng sống "
        "chung với gia đình (Đ61); (2) quyền lưu cư tại nhà riêng của bên kia "
        "(Đ63). Phù hợp khi có 'sống chung với gia đình', 'lưu cư', 'ở lại nhà "
        "riêng', 'khó khăn chỗ ở', 'nhà riêng của vợ/chồng'."
    ),
    params_schema=TruongHopNhaOGiaDinhVaLuuCuParams,
    cypher=_SEED_BLOCK.rstrip() + "\n\n" + EXPAND_AND_TIMEFILTER_CYPHER,
    params_builder=_params_builder,
)
