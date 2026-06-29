"""Template — đăng ký kết hôn sau chung sống (Đ14 K2)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from server.infrastructure.neo4j.cypher_templates import CypherTemplate
from server.infrastructure.neo4j.cypher_templates.chung_song_nhu_vo_chong._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("khia_canh_thoi_diem",)
_DIEU_14_WHITELIST = ["Luat_HNGD_2014_Dieu_14"]


class DangKyKetHonSauChungSongParams(BaseModel):
    tinh_trang_dang_ky: Literal[
        "chua_dang_ky",
        "du_dinh_dang_ky",
        "da_dang_ky_sau_chung_song",
        "khong_ro",
    ] = Field(
        description=(
            "Chưa/không đăng ký -> chua_dang_ky; sắp đăng ký -> du_dinh_dang_ky; "
            "đã đăng ký sau chung sống -> da_dang_ky_sau_chung_song."
        )
    )
    khia_canh_thoi_diem: Literal[
        "co_bat_buoc_sau_bao_lau",
        "thoi_diem_xac_lap_hon_nhan",
        "hieu_luc_thoi_gian_chung_song_truoc_do",
        "tong_quat",
    ] = Field(
        description=(
            "Bao lâu phải kết hôn -> co_bat_buoc_sau_bao_lau; hôn nhân tính từ khi nào "
            "-> thoi_diem_xac_lap_hon_nhan; thời gian chung sống trước có tính không "
            "-> hieu_luc_thoi_gian_chung_song_truoc_do."
        )
    )


_SEED_BODY = f"""
WITH $td AS td, $kc AS kc, $whitelist_dieu_ids AS wl

MATCH (hv:HanhVi:{TOPIC_LABEL} {{id: 'dang_ky_ket_hon_sau_thoi_gian_chung_song', topic: '{TOPIC}'}})

OPTIONAL MATCH (hq_kxl:HauQua:{TOPIC_LABEL} {{id: 'thoi_gian_chung_song_khong_tu_xac_lap_hon_nhan', topic: '{TOPIC}'}})
WHERE kc IN ['co_bat_buoc_sau_bao_lau', 'hieu_luc_thoi_gian_chung_song_truoc_do', 'tong_quat']
OPTIONAL MATCH (tthn_chua:TinhTrangHonNhan:{TOPIC_LABEL} {{id: 'chua_phat_sinh_quan_he_hon_nhan', topic: '{TOPIC}'}})
WHERE hq_kxl IS NOT NULL

OPTIONAL MATCH (hq_xl:HauQua:{TOPIC_LABEL} {{id: 'quan_he_hon_nhan_xac_lap_tu_thoi_diem_dang_ky', topic: '{TOPIC}'}})
WHERE kc IN ['thoi_diem_xac_lap_hon_nhan', 'tong_quat'] OR td = 'da_dang_ky_sau_chung_song'
OPTIONAL MATCH (tthn_co:TinhTrangHonNhan:{TOPIC_LABEL} {{id: 'quan_he_hon_nhan_phat_sinh_tu_dang_ky', topic: '{TOPIC}'}})
WHERE hq_xl IS NOT NULL

WITH wl, kc,
  [x IN collect(DISTINCT hv) + collect(DISTINCT hq_kxl) + collect(DISTINCT tthn_chua)
       + collect(DISTINCT hq_xl) + collect(DISTINCT tthn_co)
   WHERE x IS NOT NULL] AS seed_nodes,
  CASE kc
    WHEN 'thoi_diem_xac_lap_hon_nhan' THEN
      [x IN collect(DISTINCT hq_xl) + collect(DISTINCT tthn_co) WHERE x IS NOT NULL]
    WHEN 'co_bat_buoc_sau_bao_lau' THEN
      [x IN collect(DISTINCT hq_kxl) + collect(DISTINCT tthn_chua) WHERE x IS NOT NULL]
    WHEN 'hieu_luc_thoi_gian_chung_song_truoc_do' THEN
      [x IN collect(DISTINCT hq_kxl) + collect(DISTINCT tthn_chua) WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT hq_kxl) + collect(DISTINCT hq_xl) WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: DangKyKetHonSauChungSongParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "td": params.tinh_trang_dang_ky,
        "kc": params.khia_canh_thoi_diem,
        "whitelist_dieu_ids": _DIEU_14_WHITELIST if use_wl else [],
    }


dang_ky_ket_hon_sau_chung_song = CypherTemplate(
    name="dang_ky_ket_hon_sau_chung_song",
    description=(
        "Thời gian chung sống không tự làm phát sinh hôn nhân; quan hệ hôn nhân "
        "được xác lập từ thời điểm đăng ký (Đ14 K2). Không có quy định bắt buộc "
        "phải kết hôn sau một khoảng thời gian sống thử. "
        "Ví dụ: Sống thử bao lâu thì phải kết hôn?"
    ),
    params_schema=DangKyKetHonSauChungSongParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
