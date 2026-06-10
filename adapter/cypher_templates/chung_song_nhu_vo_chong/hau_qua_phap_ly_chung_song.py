"""Template — hậu quả pháp lý chung sống không đăng ký (Đ14-16)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.chung_song_nhu_vo_chong._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("khia_canh_hau_qua",)
_DIEU_14_16_WHITELIST = [
    "Luat_HNGD_2014_Dieu_14",
    "Luat_HNGD_2014_Dieu_15",
    "Luat_HNGD_2014_Dieu_16",
]


class HauQuaPhapLyChungSongParams(BaseModel):
    khia_canh_hau_qua: Literal[
        "quan_he_vo_chong",
        "con",
        "tai_san_nghia_vu_hop_dong",
        "tong_quat",
    ] = Field(
        description=(
            "Quan hệ vợ chồng -> quan_he_vo_chong; con -> con; "
            "tài sản/nợ/hợp đồng -> tai_san_nghia_vu_hop_dong; hỏi chung -> tong_quat."
        )
    )


_SEED_BODY = f"""
WITH $kc AS kc, $whitelist_dieu_ids AS wl

MATCH (hv:HanhVi:{TOPIC_LABEL} {{id: 'chung_song_nhu_vo_chong_khong_dang_ky', topic: '{TOPIC}'}})

OPTIONAL MATCH (hq_vc:HauQua:{TOPIC_LABEL} {{id: 'khong_phat_sinh_quyen_nghia_vu_vo_chong', topic: '{TOPIC}'}})
WHERE kc IN ['quan_he_vo_chong', 'tong_quat']
OPTIONAL MATCH (tthn:TinhTrangHonNhan:{TOPIC_LABEL} {{id: 'chua_phat_sinh_quan_he_hon_nhan', topic: '{TOPIC}'}})
WHERE hq_vc IS NOT NULL

OPTIONAL MATCH (hq_con:HauQua:{TOPIC_LABEL} {{id: 'quyen_nghia_vu_voi_con_giai_quyet_theo_quy_dinh_cha_me_con', topic: '{TOPIC}'}})
WHERE kc IN ['con', 'tong_quat']

OPTIONAL MATCH (hq_ts:HauQua:{TOPIC_LABEL} {{id: 'tai_san_nghia_vu_hop_dong_giai_quyet_theo_dieu_16', topic: '{TOPIC}'}})
WHERE kc IN ['tai_san_nghia_vu_hop_dong', 'tong_quat']

WITH wl, kc,
  [x IN collect(DISTINCT hv) + collect(DISTINCT hq_vc) + collect(DISTINCT tthn)
       + collect(DISTINCT hq_con) + collect(DISTINCT hq_ts)
   WHERE x IS NOT NULL] AS seed_nodes,
  CASE kc
    WHEN 'quan_he_vo_chong' THEN
      [x IN collect(DISTINCT hq_vc) + collect(DISTINCT tthn) WHERE x IS NOT NULL]
    WHEN 'con' THEN [x IN collect(DISTINCT hq_con) WHERE x IS NOT NULL]
    WHEN 'tai_san_nghia_vu_hop_dong' THEN [x IN collect(DISTINCT hq_ts) WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT hq_vc) + collect(DISTINCT hq_con) + collect(DISTINCT hq_ts)
       WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: HauQuaPhapLyChungSongParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "kc": params.khia_canh_hau_qua,
        "whitelist_dieu_ids": _DIEU_14_16_WHITELIST if use_wl else [],
    }


hau_qua_phap_ly_chung_song = CypherTemplate(
    name="hau_qua_phap_ly_chung_song",
    description=(
        "Hậu quả pháp lý tổng quát khi chung sống không đăng ký: không phát sinh "
        "quyền nghĩa vụ vợ chồng; con theo Đ15; tài sản/nghĩa vụ/hợp đồng theo Đ16. "
        "Ví dụ: Giải quyết hậu quả của việc nam, nữ chung sống như vợ chồng mà "
        "không đăng ký kết hôn như thế nào?"
    ),
    params_schema=HauQuaPhapLyChungSongParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
