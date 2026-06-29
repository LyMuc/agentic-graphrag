"""Template 1 — PHÂN LOẠI TÀI SẢN.

Trả lời câu hỏi: "X là tài sản chung hay riêng?", "Tài sản chung gồm những gì?",
"Quyền sử dụng đất sau kết hôn là tài sản chung hay riêng?", "Tiền trúng số có
phải tài sản chung không?", v.v.

Cách hoạt động (KG mới):
1. Match `LoaiTaiSan` theo `tinh_chat` (chung/riêng/cả hai).
2. Nếu user nêu loại tài sản cụ thể (`asset_keyword`), match đúng `id` hoặc
   match con-cháu qua `LA_LOAI_CON_CUA`.
3. Leaf nodes `CAN_CU_TAI` về legal layer → EXPAND chung.

Coverage: Q3, Q7, Q8, Q14, Q17 (một phần), Q18.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from server.infrastructure.neo4j.cypher_templates import CypherTemplate
from server.infrastructure.neo4j.cypher_templates.tai_san._common import (
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
)


class PhanLoaiTaiSanParams(BaseModel):
    loai_tai_san: Literal["chung", "rieng", "tat_ca"] = Field(
        description=(
            "Loại tài sản người dùng đang quan tâm.\n"
            "  • 'chung' nếu chỉ hỏi về tài sản chung (vd liệt kê, một phía).\n"
            "  • 'rieng' nếu chỉ hỏi về tài sản riêng.\n"
            "  • 'tat_ca' BẮT BUỘC khi câu hỏi đối chiếu/tranh chấp phân loại "
            "(vd 'X là tài sản chung hay riêng?', vợ/chồng đòi chia, 'có phải "
            "tài sản chung không' khi hai bên bất đồng, tài sản trong thời kỳ "
            "hôn nhân mà tranh chấp chung/riêng)."
        )
    )
    asset_keyword: Optional[str] = Field(
        default=None,
        description=(
            "QUY TẮC ƯU TIÊN — Câu đối chiếu/tranh chấp chung vs riêng: đặt "
            "null (dù câu có nêu trợ cấp, tiết kiệm, đất, trúng số...). Khi "
            "đó loai_tai_san phải là 'tat_ca'.\n"
            "Chỉ điền asset_keyword khi câu KHÔNG đối chiếu hai nhánh.\n\n"
            "ID THUẬT NGỮ PHÁP LÝ chuẩn trong KG (snake_case) — map từ ngữ "
            "trong câu hỏi sang ID chuẩn trước khi điền."
        ),
    )


_SEED_BODY = f"""
// ============================================================
// PHẦN 1 — SEED semantic graph (LoaiTaiSan phân loại)
// ============================================================
WITH $loai_tai_san AS lts_param, $asset_keyword AS akw, [] AS wl

WITH lts_param, akw, wl,
  CASE lts_param
    WHEN 'chung' THEN ['chung']
    WHEN 'rieng' THEN ['rieng']
    ELSE ['chung', 'rieng']
  END AS tinh_chat_list

UNWIND tinh_chat_list AS tc
MATCH (lts:LoaiTaiSan:{TOPIC_LABEL})
WHERE lts.tinh_chat = tc
  AND (
        akw IS NULL
        OR lts.id = akw
        OR EXISTS {{
            MATCH (lts)-[:LA_LOAI_CON_CUA*0..3]->(parent:LoaiTaiSan:{TOPIC_LABEL} {{id: akw}})
        }}
        OR EXISTS {{
            MATCH (child:LoaiTaiSan:{TOPIC_LABEL} {{id: akw}})-[:LA_LOAI_CON_CUA*0..3]->(lts)
        }}
        OR toLower(lts.id) CONTAINS toLower(akw)
      )

WITH wl, collect(DISTINCT lts) AS lts_list

WITH wl,
  lts_list AS seed_nodes,
  lts_list AS leaf_seed_nodes
"""


phan_loai_tai_san = CypherTemplate(
    name="phan_loai_tai_san",
    description=(
        "Phân loại tài sản: trả lời câu hỏi 'X là tài sản chung hay tài sản riêng?', "
        "'Tài sản chung gồm những gì?', 'Tài sản riêng gồm những gì?', "
        "'Y có phải tài sản chung trong thời kỳ hôn nhân không?', 'Tiền trúng số "
        "có phải tài sản chung không?'. Phù hợp khi câu hỏi tập trung vào việc "
        "XÁC ĐỊNH bản chất / phạm vi của khối tài sản, KHÔNG hỏi về quyền định "
        "đoạt, nghĩa vụ, hay chia tài sản."
    ),
    params_schema=PhanLoaiTaiSanParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
)
