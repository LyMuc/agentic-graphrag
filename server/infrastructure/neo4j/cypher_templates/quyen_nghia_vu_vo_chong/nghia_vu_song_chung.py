"""Template — nghĩa vụ sống chung và ngoại lệ (Đ19 khoản 2)."""
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

_TINH_HUONG_TO_DIEU_KIEN: dict[str, str] = {
    "thoa_thuan_song_rieng": "thoa_thuan_khong_song_chung",
    "nghe_nghiep_cong_tac": "yeu_cau_nghe_nghiep_cong_tac",
    "hoc_tap": "yeu_cau_hoc_tap",
    "hoat_dong_chinh_tri_kinh_te_van_hoa_xa_hoi": "tham_gia_hoat_dong_chinh_tri_kinh_te_van_hoa_xa_hoi",
    "ly_do_chinh_dang_khac": "ly_do_chinh_dang_khac",
}


class NghiaVuSongChungParams(BaseModel):
    tinh_huong_song_chung: Literal[
        "bat_buoc_song_chung",
        "thoa_thuan_song_rieng",
        "nghe_nghiep_cong_tac",
        "hoc_tap",
        "hoat_dong_chinh_tri_kinh_te_van_hoa_xa_hoi",
        "ly_do_chinh_dang_khac",
        "khong_ro",
    ] = Field(description="bắt buộc sống chung -> bat_buoc_song_chung; thỏa thuận sống riêng -> thoa_thuan_song_rieng.")
    khia_canh_song_chung: Literal[
        "co_nghia_vu",
        "co_thuoc_ngoai_le",
        "danh_gia_ly_do",
        "tong_quat",
        "khong_ro",
    ] = Field(description="có bắt buộc không -> co_nghia_vu; có thuộc ngoại lệ -> co_thuoc_ngoai_le.")


_SEED_BODY = f"""
WITH $th AS th, $kc AS kc, $dk_id AS dk_id, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (nv:NghiaVu:{TOPIC_LABEL} {{
  id: 'nghia_vu_song_chung', topic: '{TOPIC}'
}})

OPTIONAL MATCH (dk:DieuKien:{TOPIC_LABEL} {{id: dk_id, topic: '{TOPIC}'}})
WHERE dk_id <> ''

WITH wl, th,
  collect(DISTINCT nv) + collect(DISTINCT dk) AS seed_nodes,
  [x IN collect(DISTINCT nv) + collect(DISTINCT dk) WHERE x IS NOT NULL] AS leaf_seed_nodes
"""


def _params_builder(params: NghiaVuSongChungParams) -> dict[str, Any]:
    th = params.tinh_huong_song_chung
    dk_id = _TINH_HUONG_TO_DIEU_KIEN.get(th, "")
    return {
        "th": th,
        "kc": params.khia_canh_song_chung,
        "dk_id": dk_id,
        "whitelist_dieu_ids": [],
    }


nghia_vu_song_chung = CypherTemplate(
    name="nghia_vu_song_chung",
    description=(
        "Trả lời nghĩa vụ sống chung và các ngoại lệ tại khoản 2 Điều 19: thỏa thuận khác, "
        "yêu cầu nghề nghiệp/công tác/học tập, tham gia hoạt động xã hội hoặc lý do chính đáng. "
        "Không dùng cho hộ khẩu và lựa chọn nhà ở cụ thể. "
        "Ví dụ: Sau kết hôn có bắt buộc sống chung không?; "
        "Sống riêng vì làm việc ở tỉnh khác có thuộc ngoại lệ?; "
        "Vợ chồng thỏa thuận không sống chung có được không?"
    ),
    params_schema=NghiaVuSongChungParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
