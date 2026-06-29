"""Template — quy tắc con dưới 36 tháng tuổi (Đ81 K3)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from server.infrastructure.neo4j.cypher_templates import CypherTemplate
from server.infrastructure.neo4j.cypher_templates.cha_me_con_sau_ly_hon._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
)

_DIEU_82_K2 = "Luat_HNGD_2014_Dieu_82_Khoan_2"


class NuoiConDuoi36ThangParams(BaseModel):
    do_tuoi_con: Literal[
        "duoi_36_thang",
        "tu_36_thang_den_duoi_7_tuoi",
        "tu_du_7_tuoi",
        "khong_ro",
    ] = Field(
        description=(
            "Độ tuổi con. Map: dưới 3 tuổi/9-24 tháng/1-2 tuổi → duoi_36_thang; "
            "từ 36 tháng đến dưới 7 tuổi → tu_36_thang_den_duoi_7_tuoi; "
            "từ đủ 7 tuổi → tu_du_7_tuoi."
        )
    )
    tinh_trang_nguoi_me: Literal["du_dieu_kien", "khong_du_dieu_kien", "khong_ro"] = Field(
        description=(
            "Tình trạng mẹ. Map: mẹ chăm sóc tốt/đủ điều kiện → du_dieu_kien; "
            "mẹ bỏ đi/không đủ điều kiện → khong_du_dieu_kien."
        )
    )
    thoa_thuan_khac: Literal["co", "khong", "khong_ro"] = Field(
        description="Hai bên có thỏa thuận khác (vd cha nuôi) → co/khong/khong_ro."
    )
    ben_de_nghi_nuoi: Literal["cha", "me", "ca_hai", "khong_ro"] = Field(
        description="Bên đề nghị trực tiếp nuôi."
    )
    co_yeu_cau_cap_duong: Literal["co", "khong", "khong_ro"] = Field(
        description=(
            "Có hỏi cấp dưỡng/chu cấp → co. Chỉ seed Đ82 K2, không kéo Đ107-120."
        )
    )


_SEED_BODY = f"""
WITH $tinh_trang_nguoi_me AS ttm, $thoa_thuan_khac AS ttk, $co_yeu_cau_cap_duong AS cycd,
     $whitelist_dieu_ids AS wl

MATCH (dk36:DieuKien:{TOPIC_LABEL} {{id: 'con_duoi_ba_muoi_sau_thang_tuoi', topic: '{TOPIC}'}})
MATCH (hq36:HauQua:{TOPIC_LABEL} {{id: 'giao_con_duoi_ba_muoi_sau_thang_cho_me', topic: '{TOPIC}'}})

OPTIONAL MATCH (dk_me:DieuKien:{TOPIC_LABEL} {{id: 'me_khong_du_dieu_kien_truc_tiep_nuoi_con', topic: '{TOPIC}'}})
WHERE ttm = 'khong_du_dieu_kien'

OPTIONAL MATCH (dk_tt:DieuKien:{TOPIC_LABEL} {{
  id: 'cha_me_co_thoa_thuan_khac_phu_hop_loi_ich_con', topic: '{TOPIC}'
}})
WHERE ttk = 'co'

OPTIONAL MATCH (nv_cd:NghiaVu:{TOPIC_LABEL} {{
  id: 'nghia_vu_nguoi_khong_truc_tiep_nuoi_con', topic: '{TOPIC}'
}})
WHERE cycd = 'co'
OPTIONAL MATCH (nv_cd)-[:LIEN_KET_CAP_DUONG]->(nv_cap:NghiaVu:CapDuong {{
  id: 'nghia_vu_cap_duong_cha_me_khong_truc_tiep_nuoi_con'
}})
WHERE cycd = 'co'

WITH wl, ttm, ttk, cycd,
  collect(DISTINCT dk36) + collect(DISTINCT hq36) + collect(DISTINCT dk_me)
    + collect(DISTINCT dk_tt) + collect(DISTINCT nv_cd) + collect(DISTINCT nv_cap) AS seed_nodes,
  CASE
    WHEN ttm = 'khong_du_dieu_kien' THEN
      [x IN collect(DISTINCT dk36) + collect(DISTINCT dk_me) + collect(DISTINCT hq36)
       WHERE x IS NOT NULL]
    WHEN ttk = 'co' THEN
      [x IN collect(DISTINCT dk36) + collect(DISTINCT dk_tt) + collect(DISTINCT hq36)
       WHERE x IS NOT NULL]
    WHEN cycd = 'co' THEN
      [x IN collect(DISTINCT dk36) + collect(DISTINCT hq36) + collect(DISTINCT nv_cd)
           + collect(DISTINCT nv_cap)
       WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT dk36) + collect(DISTINCT hq36) WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: NuoiConDuoi36ThangParams) -> dict[str, Any]:
    wl: list[str] = []
    if params.co_yeu_cau_cap_duong == "co":
        wl = [_DIEU_82_K2]
    return {
        "tinh_trang_nguoi_me": params.tinh_trang_nguoi_me,
        "thoa_thuan_khac": params.thoa_thuan_khac,
        "co_yeu_cau_cap_duong": params.co_yeu_cau_cap_duong,
        "whitelist_dieu_ids": wl,
    }


nuoi_con_duoi_36_thang = CypherTemplate(
    name="nuoi_con_duoi_36_thang",
    description=(
        "Quy tắc con dưới 36 tháng tuổi được giao cho mẹ trực tiếp nuôi và ngoại lệ "
        "khi mẹ không đủ điều kiện hoặc cha mẹ có thỏa thuận khác phù hợp lợi ích con. "
        "Ví dụ: con bao nhiêu tuổi mặc nhiên giao cho mẹ; con dưới 3 tuổi có đều giao "
        "cho mẹ không; con 24 tháng tranh chấp quyền nuôi."
    ),
    params_schema=NuoiConDuoi36ThangParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
