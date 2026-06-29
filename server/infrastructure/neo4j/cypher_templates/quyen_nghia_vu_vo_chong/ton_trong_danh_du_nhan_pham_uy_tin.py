"""Template — tôn trọng danh dự, nhân phẩm, uy tín (Đ21)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from server.infrastructure.neo4j.cypher_templates import CypherTemplate
from server.infrastructure.neo4j.cypher_templates.quyen_nghia_vu_vo_chong._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
)


class TonTrongDanhDuNhanPhamUyTinParams(BaseModel):
    hanh_vi_danh_du: Literal[
        "dang_thong_tin_rieng_tu_len_mang",
        "xuc_pham_ha_thap",
        "khong_giu_gin_bao_ve",
        "liet_ke_nghia_vu",
        "tong_quat",
        "khong_ro",
    ] = Field(description="đăng thông tin riêng tư lên mạng -> dang_thong_tin_rieng_tu_len_mang.")
    doi_tuong_bi_anh_huong: Literal[
        "vo",
        "chong",
        "ca_hai",
        "khong_ro",
    ] = Field(description="danh dự vợ -> vo; câu chung -> ca_hai.")


_SEED_BODY = f"""
WITH $hv AS hv, $dt AS dt, $seed_dang_mang AS seed_dang_mang,
     $whitelist_dieu_ids AS wl

OPTIONAL MATCH (nv:NghiaVu:{TOPIC_LABEL} {{
  id: 'nghia_vu_ton_trong_giu_gin_bao_ve_danh_du_nhan_pham_uy_tin', topic: '{TOPIC}'
}})

OPTIONAL MATCH (hv_m:HanhVi:{TOPIC_LABEL} {{
  id: 'dang_thong_tin_rieng_tu_cua_vo_chong_len_mang', topic: '{TOPIC}'
}})
WHERE seed_dang_mang = true

OPTIONAL MATCH (hq:HauQua:{TOPIC_LABEL} {{
  id: 'dau_hieu_vi_pham_nghia_vu_ton_trong_danh_du', topic: '{TOPIC}'
}})
WHERE seed_dang_mang = true

WITH wl, hv,
  collect(DISTINCT nv) + collect(DISTINCT hv_m) + collect(DISTINCT hq) AS seed_nodes,
  [x IN collect(DISTINCT nv) + collect(DISTINCT hv_m) + collect(DISTINCT hq)
   WHERE x IS NOT NULL] AS leaf_seed_nodes
"""


def _params_builder(params: TonTrongDanhDuNhanPhamUyTinParams) -> dict[str, Any]:
    hv = params.hanh_vi_danh_du
    seed_dang_mang = hv == "dang_thong_tin_rieng_tu_len_mang"
    return {
        "hv": hv,
        "dt": params.doi_tuong_bi_anh_huong,
        "seed_dang_mang": seed_dang_mang,
        "whitelist_dieu_ids": [],
    }


ton_trong_danh_du_nhan_pham_uy_tin = CypherTemplate(
    name="ton_trong_danh_du_nhan_pham_uy_tin",
    description=(
        "Truy xuất nghĩa vụ tôn trọng, giữ gìn và bảo vệ danh dự, nhân phẩm, uy tín của nhau "
        "theo Điều 21. Dùng cho câu hỏi liệt kê nghĩa vụ hoặc hành vi công khai thông tin riêng tư. "
        "Ví dụ: Nghĩa vụ tôn trọng danh dự vợ chồng được quy định thế nào?; "
        "Chồng đăng thông tin riêng tư của vợ lên mạng có vi phạm?"
    ),
    params_schema=TonTrongDanhDuNhanPhamUyTinParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
