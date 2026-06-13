"""Template — điều kiện kết hôn tổng quát (Đ8 K1-K2)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.dieu_kien_ket_hon._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("khia_canh_tong_quat",)
_DIEU_WHITELIST = ["Luat_HNGD_2014_Dieu_5", "Luat_HNGD_2014_Dieu_8"]


class DieuKienKetHonTongQuatParams(BaseModel):
    khia_canh_tong_quat: Literal[
        "liet_ke_dieu_kien",
        "giai_thich_khai_niem",
        "kiem_tra_day_du",
        "tong_quat",
    ] = Field(
        description=(
            "cần đáp ứng những gì -> liet_ke_dieu_kien; "
            "là gì -> giai_thich_khai_niem; "
            "đã đủ hết chưa -> kiem_tra_day_du."
        )
    )
    muc_do_chi_tiet: Literal[
        "chi_dieu_8_khoan_1",
        "kem_khoan_2_cung_gioi",
        "kem_dinh_nghia_ket_hon",
        "day_du",
    ] = Field(
        description=(
            "mặc định liệt kê -> kem_khoan_2_cung_gioi; "
            "câu hỏi là gì/khái niệm -> kem_dinh_nghia_ket_hon hoặc day_du."
        )
    )


_SEED_BODY = f"""
WITH $kc AS kc, $md AS md, $whitelist_dieu_ids AS wl

MATCH (dk:DieuKien:{TOPIC_LABEL} {{id: 'du_dieu_kien_ket_hon', topic: '{TOPIC}'}})
OPTIONAL MATCH (dk)-[:BAO_GOM]->(dk_leaf:DieuKien:{TOPIC_LABEL})
WHERE dk_leaf.topic = '{TOPIC}'

OPTIONAL MATCH (qh:QuanHe:{TOPIC_LABEL} {{id: 'hon_nhan_cung_gioi_tinh', topic: '{TOPIC}'}})
WHERE md IN ['kem_khoan_2_cung_gioi', 'day_du']
OPTIONAL MATCH (hq:HauQua:{TOPIC_LABEL} {{
  id: 'hon_nhan_cung_gioi_khong_duoc_nha_nuoc_thua_nhan', topic: '{TOPIC}'
}})
WHERE qh IS NOT NULL

OPTIONAL MATCH (qd_dn:QuyDinh:{TOPIC_LABEL} {{id: 'dinh_nghia_ket_hon', topic: '{TOPIC}'}})
WHERE md IN ['kem_dinh_nghia_ket_hon', 'day_du']

WITH wl, kc,
  [x IN collect(DISTINCT dk) + collect(DISTINCT dk_leaf)
       + collect(DISTINCT qh) + collect(DISTINCT hq) + collect(DISTINCT qd_dn)
   WHERE x IS NOT NULL] AS seed_nodes,
  [x IN collect(DISTINCT dk) + collect(DISTINCT dk_leaf)
       + collect(DISTINCT qh) + collect(DISTINCT hq) + collect(DISTINCT qd_dn)
   WHERE x IS NOT NULL] AS leaf_seed_nodes
"""


def _params_builder(params: DieuKienKetHonTongQuatParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "kc": params.khia_canh_tong_quat,
        "md": params.muc_do_chi_tiet,
        "whitelist_dieu_ids": _DIEU_WHITELIST if use_wl else [],
    }


dieu_kien_ket_hon_tong_quat = CypherTemplate(
    name="dieu_kien_ket_hon_tong_quat",
    description=(
        "Trả lời câu hỏi khái quát điều kiện kết hôn là gì/cần đáp ứng gì, lấy đủ "
        "bốn nhóm tại khoản 1 Điều 8 và ghi riêng quy tắc khoản 2 về hôn nhân cùng giới. "
        "Không dùng cho câu đã có trọng tâm tuổi, quan hệ thân thích, cùng giới "
        "hoặc hoàn cảnh cụ thể. "
        "Ví dụ: Muốn kết hôn cần đáp ứng điều kiện nào?; "
        "Điều kiện kết hôn là gì?"
    ),
    params_schema=DieuKienKetHonTongQuatParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
