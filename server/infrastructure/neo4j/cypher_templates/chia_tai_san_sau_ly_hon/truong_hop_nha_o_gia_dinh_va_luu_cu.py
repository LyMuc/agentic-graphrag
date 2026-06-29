"""Template 5 — TRƯỜNG HỢP NHÀ Ở GIA ĐÌNH VÀ LƯU CƯ (Đ61, Đ63).

Coverage feat_llm stt: 12,18.
Seed kiểu semantic graph: AP_DUNG_KHI + DAN_TOI trên Đ61/Đ63.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from server.infrastructure.neo4j.cypher_templates import CypherTemplate
from server.infrastructure.neo4j.cypher_templates.chia_tai_san_sau_ly_hon._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("loai_truong_hop",)


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


_SEED_BODY = f"""
// ============================================================
// PHẦN 1 — SEED semantic graph (sống chung gia đình / lưu cư)
// ============================================================
WITH $loai_truong_hop AS lth,
     $xac_dinh_duoc_phan_tai_san AS xdp,
     $kho_khan_cho_o AS kko,
     $whitelist_dieu_ids AS wl

OPTIONAL MATCH (hv61:HanhVi:{TOPIC_LABEL} {{id: 'chia_tai_san_song_chung_voi_gia_dinh', topic: '{TOPIC}'}})
WHERE lth IN ['song_chung_voi_gia_dinh', 'tat_ca']

OPTIONAL MATCH (hv61)-[:AP_DUNG_KHI]->(dk61:DieuKien:{TOPIC_LABEL})
WHERE lth IN ['song_chung_voi_gia_dinh', 'tat_ca']
  AND (
    xdp = 'khong_ro'
    OR dk61.id = CASE xdp
         WHEN 'khong' THEN 'tai_san_vo_chong_trong_khoi_gia_dinh_khong_xac_dinh_duoc'
         ELSE 'tai_san_vo_chong_trong_khoi_gia_dinh_xac_dinh_duoc_theo_phan'
       END
  )

OPTIONAL MATCH (luu:HauQua:{TOPIC_LABEL} {{id: 'luu_cu_sau_ly_hon', topic: '{TOPIC}'}})
WHERE lth IN ['luu_cu_nha_rieng', 'tat_ca']

OPTIONAL MATCH (luu)-[:AP_DUNG_KHI]->(lts:LoaiTaiSan:{TOPIC_LABEL})
WHERE lth IN ['luu_cu_nha_rieng', 'tat_ca']

OPTIONAL MATCH (luu)-[:AP_DUNG_KHI]->(dk63:DieuKien:{TOPIC_LABEL} {{id: 'kho_khan_ve_cho_o'}})
WHERE lth IN ['luu_cu_nha_rieng', 'tat_ca']
  AND kko IN ['co', 'khong_ro']

OPTIONAL MATCH (luu)-[:DAN_TOI]->(th:HauQua:{TOPIC_LABEL} {{id: 'thoi_han_luu_cu_06_thang'}})
WHERE lth IN ['luu_cu_nha_rieng', 'tat_ca']

WITH wl, xdp,
  [x IN collect(DISTINCT hv61) + collect(DISTINCT dk61)
       + collect(DISTINCT luu) + collect(DISTINCT lts)
       + collect(DISTINCT dk63) + collect(DISTINCT th)
   WHERE x IS NOT NULL] AS seed_nodes,
  CASE
    WHEN xdp IN ['khong', 'co'] THEN
      [x IN collect(DISTINCT dk61) WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT hv61) + collect(DISTINCT dk61) WHERE x IS NOT NULL]
  END
    + [x IN collect(DISTINCT luu) + collect(DISTINCT lts)
         + collect(DISTINCT dk63) + collect(DISTINCT th)
       WHERE x IS NOT NULL] AS leaf_seed_nodes
"""


def _params_builder(params: TruongHopNhaOGiaDinhVaLuuCuParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    wl: list[str] = []
    if use_wl:
        if params.loai_truong_hop in ("song_chung_voi_gia_dinh", "tat_ca"):
            wl.append("Luat_HNGD_2014_Dieu_61")
        if params.loai_truong_hop in ("luu_cu_nha_rieng", "tat_ca"):
            wl.append("Luat_HNGD_2014_Dieu_63")
    return {
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
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
