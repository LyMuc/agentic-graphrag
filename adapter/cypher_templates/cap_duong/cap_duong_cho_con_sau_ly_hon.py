"""Template — cấp dưỡng cho con khi cha/mẹ không trực tiếp nuôi (Đ82 K2)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.cap_duong._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
)

_DIEU_82_K2 = "Luat_HNGD_2014_Dieu_82_Khoan_2"


class CapDuongChoConSauLyHonParams(BaseModel):
    khia_canh: Literal[
        "nghia_vu_nguoi_khong_truc_tiep_nuoi",
        "khong_yeu_cau_nhan_cap_duong",
        "thay_doi_nguoi_truc_tiep_nuoi",
        "quyen_nghia_vu_sau_ly_hon",
        "tong_quat",
    ] = Field(
        description=(
            "Khía cạnh. Map: không trực tiếp nuôi/phải cấp dưỡng "
            "→ nghia_vu_nguoi_khong_truc_tiep_nuoi; không muốn nhận tiền "
            "→ khong_yeu_cau_nhan_cap_duong; đổi người nuôi con "
            "→ thay_doi_nguoi_truc_tiep_nuoi; hỏi cả quyền/nghĩa vụ "
            "→ quyen_nghia_vu_sau_ly_hon."
        )
    )
    nguoi_khong_truc_tiep_nuoi: Literal["cha", "me", "khong_ro"] = Field(
        description="cha/mẹ không trực tiếp nuôi con."
    )
    tinh_trang_thuc_hien: Literal[
        "tu_nguyen",
        "khong_yeu_cau",
        "khong_thuc_hien",
        "thay_doi_nguoi_nuoi",
        "khong_ro",
    ] = Field(description="Tình trạng thực hiện nghĩa vụ cấp dưỡng.")


_SEED_BODY = f"""
WITH $khia_canh AS kc, $whitelist_dieu_ids AS wl

MATCH (qh:QuanHeCapDuong:{TOPIC_LABEL} {{
  id: 'cha_me_khong_truc_tiep_nuoi_con_sau_ly_hon', topic: '{TOPIC}'
}})
MATCH (qh)-[:QUY_DINH_NGHIA_VU]->(nv:NghiaVu:{TOPIC_LABEL} {{
  id: 'nghia_vu_cap_duong_cha_me_khong_truc_tiep_nuoi_con', topic: '{TOPIC}'
}})

OPTIONAL MATCH (nv_gen:NghiaVu:{TOPIC_LABEL} {{id: 'nghia_vu_cap_duong', topic: '{TOPIC}'}})
WHERE kc = 'thay_doi_nguoi_truc_tiep_nuoi'

OPTIONAL MATCH (tt:ThoaThuan:{TOPIC_LABEL} {{id: 'thoa_thuan_muc_cap_duong', topic: '{TOPIC}'}})
WHERE kc IN ['quyen_nghia_vu_sau_ly_hon', 'tong_quat']

WITH wl, kc,
  collect(DISTINCT qh) AS qhs,
  collect(DISTINCT nv) AS nvs,
  collect(DISTINCT nv_gen) AS nv_gens,
  collect(DISTINCT tt) AS tts

WITH wl, kc, qhs, nvs, nv_gens, tts,
  [x IN qhs + nvs + nv_gens + tts WHERE x IS NOT NULL] AS seed_nodes,
  CASE kc
    WHEN 'thay_doi_nguoi_truc_tiep_nuoi' THEN
      [x IN qhs + nvs + nv_gens WHERE x IS NOT NULL]
    ELSE
      [x IN qhs + nvs WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: CapDuongChoConSauLyHonParams) -> dict[str, Any]:
    return {
        "khia_canh": params.khia_canh,
        "whitelist_dieu_ids": [_DIEU_82_K2],
    }


cap_duong_cho_con_sau_ly_hon = CypherTemplate(
    name="cap_duong_cho_con_sau_ly_hon",
    description=(
        "Nghĩa vụ cấp dưỡng cho con của cha hoặc mẹ không trực tiếp nuôi con sau ly hôn "
        "(Đ82 khoản 2), gồm không yêu cầu nhận cấp dưỡng và thay đổi người trực tiếp nuôi. "
        "Ví dụ: người không trực tiếp nuôi con thì có nghĩa vụ và quyền gì; "
        "nghĩa vụ cấp dưỡng có thay đổi sau khi thay đổi người trực tiếp nuôi con hay không."
    ),
    params_schema=CapDuongChoConSauLyHonParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
