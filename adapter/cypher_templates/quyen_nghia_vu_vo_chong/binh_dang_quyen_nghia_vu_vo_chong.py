"""Template — bình đẳng quyền, nghĩa vụ vợ chồng (Đ17)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.quyen_nghia_vu_vo_chong._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("khia_canh_binh_dang",)
_DIEU_WHITELIST = [f"Luat_HNGD_2014_Dieu_{i}" for i in range(17, 24)]


class BinhDangQuyenNghiaVuVoChongParams(BaseModel):
    khia_canh_binh_dang: Literal[
        "quyen_nghia_vu_ngang_nhau",
        "pham_vi_moi_mat_trong_gia_dinh",
        "quyet_dinh_cong_viec_gia_dinh",
        "tong_quat",
        "khong_ro",
    ] = Field(
        description=(
            "quyền và nghĩa vụ ngang nhau -> quyen_nghia_vu_ngang_nhau; "
            "mọi mặt trong gia đình -> pham_vi_moi_mat_trong_gia_dinh; "
            "tự quyết mọi việc -> quyet_dinh_cong_viec_gia_dinh."
        )
    )
    chu_the_quyet_dinh: Literal[
        "ca_hai_vo_chong",
        "vo",
        "chong",
        "nguoi_khac",
        "khong_ro",
    ] = Field(description="Chủ thể tự quyết hoặc bị hỏi quyền quyết định.")


_SEED_BODY = f"""
WITH $kc AS kc, $ct AS ct, $seed_quyet_dinh AS seed_quyet_dinh,
     $whitelist_dieu_ids AS wl

OPTIONAL MATCH (anchor:QuyDinh:{TOPIC_LABEL} {{
  id: 'binh_dang_quyen_nghia_vu_giua_vo_chong', topic: '{TOPIC}'
}})

OPTIONAL MATCH (leaf_qn:Quyen:{TOPIC_LABEL} {{
  id: 'quyen_nghia_vu_ngang_nhau_moi_mat_trong_gia_dinh', topic: '{TOPIC}'
}})
WHERE kc IN ['quyen_nghia_vu_ngang_nhau', 'pham_vi_moi_mat_trong_gia_dinh', 'tong_quat']

OPTIONAL MATCH (hv:HanhVi:{TOPIC_LABEL} {{
  id: 'mot_ben_tu_quyet_moi_viec_trong_gia_dinh', topic: '{TOPIC}'
}})
WHERE seed_quyet_dinh = true

OPTIONAL MATCH (hq:HauQua:{TOPIC_LABEL} {{
  id: 'dau_hieu_xam_pham_nguyen_tac_binh_dang_vo_chong', topic: '{TOPIC}'
}})
WHERE seed_quyet_dinh = true

WITH wl, kc,
  collect(DISTINCT anchor) + collect(DISTINCT leaf_qn)
    + collect(DISTINCT hv) + collect(DISTINCT hq)
    AS seed_nodes,
  [x IN collect(DISTINCT leaf_qn) + collect(DISTINCT hv) + collect(DISTINCT hq)
   WHERE x IS NOT NULL] AS leaf_seed_nodes
"""


def _params_builder(params: BinhDangQuyenNghiaVuVoChongParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    kc = params.khia_canh_binh_dang
    seed_quyet_dinh = kc == "quyet_dinh_cong_viec_gia_dinh" or params.chu_the_quyet_dinh in (
        "chong",
        "vo",
    )
    return {
        "kc": kc,
        "ct": params.chu_the_quyet_dinh,
        "seed_quyet_dinh": seed_quyet_dinh,
        "whitelist_dieu_ids": _DIEU_WHITELIST if use_wl else [],
    }


binh_dang_quyen_nghia_vu_vo_chong = CypherTemplate(
    name="binh_dang_quyen_nghia_vu_vo_chong",
    description=(
        "Trả lời nguyên tắc vợ chồng bình đẳng, có quyền và nghĩa vụ ngang nhau về mọi mặt "
        "trong gia đình và khi thực hiện quyền, nghĩa vụ công dân. Dùng khi một bên cho rằng "
        "mình có quyền tự quyết mọi việc chỉ vì là chồng hoặc vợ. "
        "Ví dụ: Quyền và nghĩa vụ ngang nhau có phải là bình đẳng?; "
        "Chồng tự quyết mọi việc trong gia đình mà không hỏi ý vợ."
    ),
    params_schema=BinhDangQuyenNghiaVuVoChongParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
