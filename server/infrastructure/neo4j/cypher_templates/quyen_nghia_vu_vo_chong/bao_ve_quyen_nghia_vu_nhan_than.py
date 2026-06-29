"""Template — bảo vệ quyền, nghĩa vụ nhân thân vợ chồng (Đ18)."""
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

_ROUTER_FIELDS = ("dang_xam_pham_nhan_than",)


class BaoVeQuyenNghiaVuNhanThanParams(BaseModel):
    dang_xam_pham_nhan_than: Literal[
        "can_thiep_quyen_tu_do_ca_nhan",
        "khong_ton_trong_quyen_nhan_than",
        "hoi_co_che_bao_ve",
        "tong_quat",
        "khong_ro",
    ] = Field(
        description=(
            "can thiệp quyền tự do cá nhân -> can_thiep_quyen_tu_do_ca_nhan; "
            "được tôn trọng và bảo vệ thế nào -> hoi_co_che_bao_ve."
        )
    )
    chu_the_can_thiep: Literal[
        "vo",
        "chong",
        "gia_dinh_vo",
        "gia_dinh_chong",
        "nguoi_khac",
        "khong_ro",
    ] = Field(description="gia đình chồng -> gia_dinh_chong.")


_SEED_BODY = f"""
WITH $dx AS dx, $ct AS ct, $seed_can_thiep AS seed_can_thiep,
     $whitelist_dieu_ids AS wl

OPTIONAL MATCH (anchor:QuyDinh:{TOPIC_LABEL} {{
  id: 'quyen_nghia_vu_nhan_than_duoc_ton_trong_bao_ve', topic: '{TOPIC}'
}})

OPTIONAL MATCH (leaf:Quyen:{TOPIC_LABEL} {{
  id: 'quyen_nhan_than_cua_vo_chong', topic: '{TOPIC}'
}})
WHERE dx IN ['hoi_co_che_bao_ve', 'tong_quat', 'khong_ro', 'khong_ton_trong_quyen_nhan_than']

OPTIONAL MATCH (hv:HanhVi:{TOPIC_LABEL} {{
  id: 'gia_dinh_chong_can_thiep_quyen_tu_do_ca_nhan_cua_vo', topic: '{TOPIC}'
}})
WHERE seed_can_thiep = true

OPTIONAL MATCH (hq:HauQua:{TOPIC_LABEL} {{
  id: 'dau_hieu_xam_pham_quyen_nhan_than_cua_vo_chong', topic: '{TOPIC}'
}})
WHERE seed_can_thiep = true

WITH wl, dx,
  collect(DISTINCT anchor) + collect(DISTINCT leaf)
    + collect(DISTINCT hv) + collect(DISTINCT hq)
    AS seed_nodes,
  [x IN collect(DISTINCT leaf) + collect(DISTINCT hv) + collect(DISTINCT hq)
   WHERE x IS NOT NULL] AS leaf_seed_nodes
"""


def _params_builder(params: BaoVeQuyenNghiaVuNhanThanParams) -> dict[str, Any]:
    dx = params.dang_xam_pham_nhan_than
    ct = params.chu_the_can_thiep
    seed_can_thiep = dx == "can_thiep_quyen_tu_do_ca_nhan" and ct in (
        "gia_dinh_chong",
        "gia_dinh_vo",
        "nguoi_khac",
    )
    return {
        "dx": dx,
        "ct": ct,
        "seed_can_thiep": seed_can_thiep,
        "whitelist_dieu_ids": [],
    }


bao_ve_quyen_nghia_vu_nhan_than = CypherTemplate(
    name="bao_ve_quyen_nghia_vu_nhan_than",
    description=(
        "Truy xuất quy tắc quyền, nghĩa vụ nhân thân của vợ chồng được tôn trọng và bảo vệ "
        "theo Điều 18. Dùng cho câu hỏi nhân thân tổng quát hoặc sự can thiệp của người thân "
        "vào quyền tự do cá nhân. "
        "Ví dụ: Quyền nhân thân của vợ chồng được bảo vệ như thế nào?; "
        "Gia đình chồng can thiệp quyền tự do cá nhân của vợ."
    ),
    params_schema=BaoVeQuyenNghiaVuNhanThanParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
