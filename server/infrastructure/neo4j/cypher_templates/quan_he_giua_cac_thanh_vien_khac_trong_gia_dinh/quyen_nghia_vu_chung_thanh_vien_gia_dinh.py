"""Template — quyền, nghĩa vụ chung thành viên gia đình (Đ103 K1, K3)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from server.infrastructure.neo4j.cypher_templates import CypherTemplate
from server.infrastructure.neo4j.cypher_templates.quan_he_giua_cac_thanh_vien_khac_trong_gia_dinh._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("khia_canh_chung",)
_DIEU_WHITELIST = ["Luat_HNGD_2014_Dieu_103"]


class QuyenNghiaVuChungThanhVienGiaDinhParams(BaseModel):
    khia_canh_chung: Literal[
        "quyen_nghia_vu_chung",
        "bao_ve_quyen_loi",
        "chinh_sach_nha_nuoc",
        "tong_quat",
    ] = Field(description="quyền nghĩa vụ chung / bảo vệ quyền lợi / chính sách Nhà nước.")
    nhom_noi_dung: Literal[
        "quan_tam_cham_soc_giup_do_ton_trong",
        "nhan_than_va_tai_san",
        "giu_gin_truyen_thong_gia_dinh",
        "tong_hop",
    ] = Field(description="nhóm nội dung câu hỏi Điều 103.")


_SEED_BODY = f"""
WITH $khia_canh_chung AS kc, $nhom_noi_dung AS nd, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (qd:QuyDinh:{TOPIC_LABEL} {{
  id: 'quy_dinh_chung_quyen_nghia_vu_thanh_vien_gia_dinh', topic: '{TOPIC}'
}})
WHERE kc IN ['quyen_nghia_vu_chung', 'tong_quat']
OPTIONAL MATCH (q_qt:Quyen:{TOPIC_LABEL} {{
  id: 'quyen_duoc_quan_tam_cham_soc_giup_do_ton_trong', topic: '{TOPIC}'
}})
WHERE kc IN ['quyen_nghia_vu_chung', 'tong_quat']
  OR nd IN ['quan_tam_cham_soc_giup_do_ton_trong', 'tong_hop']
OPTIONAL MATCH (nv_qt:NghiaVu:{TOPIC_LABEL} {{
  id: 'nghia_vu_quan_tam_cham_soc_giup_do_ton_trong_lan_nhau', topic: '{TOPIC}'
}})
WHERE kc IN ['quyen_nghia_vu_chung', 'tong_quat']
  OR nd IN ['quan_tam_cham_soc_giup_do_ton_trong', 'tong_hop']

OPTIONAL MATCH (q_bv:Quyen:{TOPIC_LABEL} {{
  id: 'quyen_loi_ich_nhan_than_va_tai_san_duoc_bao_ve', topic: '{TOPIC}'
}})
WHERE kc = 'bao_ve_quyen_loi'
  OR nd IN ['nhan_than_va_tai_san', 'tong_hop']
  OR kc = 'tong_quat'

OPTIONAL MATCH (qd_nn1:QuyDinh:{TOPIC_LABEL} {{
  id: 'nha_nuoc_tao_dieu_kien_cac_the_he_quan_tam_cham_soc_giup_do_nhau', topic: '{TOPIC}'
}})
WHERE kc = 'chinh_sach_nha_nuoc' OR kc = 'tong_quat'
OPTIONAL MATCH (qd_nn2:QuyDinh:{TOPIC_LABEL} {{
  id: 'nha_nuoc_khuyen_khich_xa_hoi_giu_gin_truyen_thong_gia_dinh', topic: '{TOPIC}'
}})
WHERE kc = 'chinh_sach_nha_nuoc'
  OR nd = 'giu_gin_truyen_thong_gia_dinh'
  OR kc = 'tong_quat'

WITH wl, kc,
  collect(DISTINCT qd) + collect(DISTINCT q_qt) + collect(DISTINCT nv_qt)
    + collect(DISTINCT q_bv) + collect(DISTINCT qd_nn1) + collect(DISTINCT qd_nn2) AS seed_nodes,
  [x IN collect(DISTINCT qd) + collect(DISTINCT q_qt) + collect(DISTINCT nv_qt)
       + collect(DISTINCT q_bv) + collect(DISTINCT qd_nn1) + collect(DISTINCT qd_nn2)
   WHERE x IS NOT NULL] AS leaf_seed_nodes
"""


def _params_builder(params: QuyenNghiaVuChungThanhVienGiaDinhParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "khia_canh_chung": params.khia_canh_chung,
        "nhom_noi_dung": params.nhom_noi_dung,
        "whitelist_dieu_ids": _DIEU_WHITELIST if use_wl else [],
    }


quyen_nghia_vu_chung_thanh_vien_gia_dinh = CypherTemplate(
    name="quyen_nghia_vu_chung_thanh_vien_gia_dinh",
    description=(
        "Dùng cho quy định chung tại Điều 103 khoản 1 và chính sách Nhà nước tại khoản 3, "
        "không dùng cho nghĩa vụ vật chất khi các thành viên đang sống chung. "
        "Ví dụ: Các thành viên khác trong gia đình có những quyền, nghĩa vụ gì đối với nhau?; "
        "Nhà nước có chính sách gì để khuyến khích các thế hệ trong gia đình quan tâm, chăm sóc, giúp đỡ nhau?"
    ),
    params_schema=QuyenNghiaVuChungThanhVienGiaDinhParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
