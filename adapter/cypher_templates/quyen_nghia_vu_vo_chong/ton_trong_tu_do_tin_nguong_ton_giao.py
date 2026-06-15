"""Template — tôn trọng quyền tự do tín ngưỡng, tôn giáo (Đ22)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.quyen_nghia_vu_vo_chong._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
)


class TonTrongTuDoTinNguongTonGiaoParams(BaseModel):
    hanh_vi_tin_nguong: Literal[
        "cam_can_thuc_hanh_ton_giao",
        "ep_buoc_theo_ton_giao",
        "khong_ton_trong_tu_do_tin_nguong",
        "liet_ke_nghia_vu",
        "tong_quat",
        "khong_ro",
    ] = Field(description="cấm đi lễ/cấm theo đạo -> cam_can_thuc_hanh_ton_giao.")
    doi_tuong_bi_anh_huong: Literal[
        "vo",
        "chong",
        "ca_hai",
        "khong_ro",
    ] = Field(description="cấm vợ -> vo; cấm chồng -> chong.")


_SEED_BODY = f"""
WITH $hv AS hv, $dt AS dt, $seed_cam AS seed_cam, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (q:Quyen:{TOPIC_LABEL} {{
  id: 'quyen_tu_do_tin_nguong_ton_giao', topic: '{TOPIC}'
}})

OPTIONAL MATCH (nv:NghiaVu:{TOPIC_LABEL} {{
  id: 'nghia_vu_ton_trong_tu_do_tin_nguong_ton_giao', topic: '{TOPIC}'
}})

OPTIONAL MATCH (hv_c:HanhVi:{TOPIC_LABEL} {{
  id: 'cam_can_thuc_hanh_ton_giao', topic: '{TOPIC}'
}})
WHERE seed_cam = true

OPTIONAL MATCH (hq:HauQua:{TOPIC_LABEL} {{
  id: 'dau_hieu_vi_pham_nghia_vu_ton_trong_tu_do_tin_nguong', topic: '{TOPIC}'
}})
WHERE seed_cam = true

WITH wl, hv,
  collect(DISTINCT q) + collect(DISTINCT nv)
    + collect(DISTINCT hv_c) + collect(DISTINCT hq)
    AS seed_nodes,
  [x IN collect(DISTINCT q) + collect(DISTINCT nv)
       + collect(DISTINCT hv_c) + collect(DISTINCT hq)
   WHERE x IS NOT NULL] AS leaf_seed_nodes
"""


def _params_builder(params: TonTrongTuDoTinNguongTonGiaoParams) -> dict[str, Any]:
    hv = params.hanh_vi_tin_nguong
    seed_cam = hv in ("cam_can_thuc_hanh_ton_giao", "ep_buoc_theo_ton_giao")
    return {
        "hv": hv,
        "dt": params.doi_tuong_bi_anh_huong,
        "seed_cam": seed_cam,
        "whitelist_dieu_ids": [],
    }


ton_trong_tu_do_tin_nguong_ton_giao = CypherTemplate(
    name="ton_trong_tu_do_tin_nguong_ton_giao",
    description=(
        "Truy xuất quyền tự do tín ngưỡng, tôn giáo và nghĩa vụ vợ chồng tôn trọng quyền đó "
        "của nhau theo Điều 22. Dùng cho câu hỏi chung hoặc hành vi cấm cản đi lễ, thực hành tôn giáo. "
        "Ví dụ: Vợ chồng có nghĩa vụ tôn trọng quyền tự do tín ngưỡng không?; "
        "Chồng cấm vợ đi lễ có vi phạm luật?"
    ),
    params_schema=TonTrongTuDoTinNguongTonGiaoParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
