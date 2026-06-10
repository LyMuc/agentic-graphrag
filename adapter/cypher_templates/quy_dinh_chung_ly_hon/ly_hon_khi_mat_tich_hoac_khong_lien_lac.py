"""Template — ly hôn khi mất tích hoặc không liên lạc (Đ56 K2, BLDS 68)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.quy_dinh_chung_ly_hon._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("tinh_trang",)
_DIEU_56_WHITELIST = ["Luat_HNGD_2014_Dieu_56"]
_BLDS_68_WHITELIST = ["BoLuat_DanSu_2015_Dieu_68"]


class LyHonKhiMatTichHoacKhongLienLacParams(BaseModel):
    tinh_trang: Literal[
        "da_bi_toa_tuyen_bo_mat_tich",
        "biet_tich_tu_hai_nam_chua_tuyen_bo",
        "khong_lien_lac_chua_ro_thoi_gian",
        "mat_tich_theo_cach_noi_thong_thuong",
        "khong_ro",
    ] = Field(
        description=(
            "Tòa đã tuyên bố mất tích → da_bi_toa_tuyen_bo_mat_tich; "
            "biệt tích 2+ năm chưa có quyết định → biet_tich_tu_hai_nam_chua_tuyen_bo; "
            "chỉ không liên lạc → khong_lien_lac_chua_ro_thoi_gian."
        )
    )
    da_thong_bao_tim_kiem: Literal["co", "khong", "khong_ro"] = Field(
        description="Đã đăng tin/tìm kiếm → co."
    )
    khia_canh_mat_tich: Literal[
        "co_duoc_ly_hon",
        "dieu_kien_tuyen_bo_mat_tich",
        "trinh_tu_truoc_khi_ly_hon",
        "tong_quat",
    ] = Field(
        description=(
            "Có ly hôn được không → co_duoc_ly_hon; điều kiện mất tích "
            "→ dieu_kien_tuyen_bo_mat_tich; phải làm gì trước → trinh_tu_truoc_khi_ly_hon."
        )
    )
    chu_the_vang_mat: Literal["vo", "chong", "khong_ro"] = Field(
        description="Người không có tin tức (debug/description)."
    )


_SEED_BODY = f"""
WITH $tt AS tt, $tim_kiem AS tk, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (ht:HinhThucLyHon:{TOPIC_LABEL} {{id: 'ly_hon_voi_nguoi_bi_tuyen_bo_mat_tich', topic: '{TOPIC}'}})
WHERE tt IN ['da_bi_toa_tuyen_bo_mat_tich', 'tong_quat']
OPTIONAL MATCH (dk_tb:DieuKien:{TOPIC_LABEL} {{id: 'da_bi_toa_an_tuyen_bo_mat_tich', topic: '{TOPIC}'}})
WHERE ht IS NOT NULL
OPTIONAL MATCH (hq_tb:HauQua:{TOPIC_LABEL} {{id: 'toa_an_giai_quyet_ly_hon_nguoi_bi_tuyen_bo_mat_tich', topic: '{TOPIC}'}})
WHERE ht IS NOT NULL

OPTIONAL MATCH (dk_bt:DieuKien:{TOPIC_LABEL} {{id: 'biet_tich_hai_nam_da_ap_dung_bien_phap_tim_kiem', topic: '{TOPIC}'}})
WHERE tt IN ['biet_tich_tu_hai_nam_chua_tuyen_bo', 'khong_lien_lac_chua_ro_thoi_gian',
             'mat_tich_theo_cach_noi_thong_thuong', 'tong_quat', 'khong_ro']
  AND (tt <> 'biet_tich_tu_hai_nam_chua_tuyen_bo' OR tk IN ['co', 'khong_ro'])

OPTIONAL MATCH (dk_mt:DieuKien:{TOPIC_LABEL} {{id: 'da_bi_toa_an_tuyen_bo_mat_tich', topic: '{TOPIC}'}})
WHERE dk_bt IS NOT NULL AND tt <> 'da_bi_toa_tuyen_bo_mat_tich'

OPTIONAL MATCH (ht2:HinhThucLyHon:{TOPIC_LABEL} {{id: 'ly_hon_voi_nguoi_bi_tuyen_bo_mat_tich', topic: '{TOPIC}'}})
WHERE dk_bt IS NOT NULL OR tt IN ['khong_lien_lac_chua_ro_thoi_gian', 'mat_tich_theo_cach_noi_thong_thuong']

WITH wl, tt,
  [x IN collect(DISTINCT ht) + collect(DISTINCT dk_tb) + collect(DISTINCT hq_tb)
       + collect(DISTINCT dk_bt) + collect(DISTINCT dk_mt) + collect(DISTINCT ht2)
   WHERE x IS NOT NULL] AS seed_nodes,
  CASE tt
    WHEN 'da_bi_toa_tuyen_bo_mat_tich' THEN
      [x IN collect(DISTINCT ht) + collect(DISTINCT dk_tb) + collect(DISTINCT hq_tb)
       WHERE x IS NOT NULL]
    WHEN 'biet_tich_tu_hai_nam_chua_tuyen_bo' THEN
      [x IN collect(DISTINCT dk_bt) + collect(DISTINCT dk_mt) + collect(DISTINCT ht2)
       WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT dk_bt) + collect(DISTINCT ht2) WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: LyHonKhiMatTichHoacKhongLienLacParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    whitelist: list[str] = []
    if use_wl:
        whitelist.extend(_DIEU_56_WHITELIST)
    if params.tinh_trang in (
        "biet_tich_tu_hai_nam_chua_tuyen_bo",
        "khong_lien_lac_chua_ro_thoi_gian",
        "mat_tich_theo_cach_noi_thong_thuong",
        "khong_ro",
    ):
        whitelist.extend(_BLDS_68_WHITELIST)
    return {
        "tt": params.tinh_trang,
        "tim_kiem": params.da_thong_bao_tim_kiem,
        "whitelist_dieu_ids": list(dict.fromkeys(whitelist)),
    }


ly_hon_khi_mat_tich_hoac_khong_lien_lac = CypherTemplate(
    name="ly_hon_khi_mat_tich_hoac_khong_lien_lac",
    description=(
        "Phân biệt mất tích/biệt tích nói chung với trạng thái đã bị Tòa án tuyên bố "
        "mất tích (Đ56 K2, BLDS 68). Biệt tích chưa có quyết định cần đủ điều kiện "
        "BLDS trước khi ly hôn. "
        "Ví dụ: Có được ly hôn chồng đang mất tích không; "
        "Người đã bị Tòa án tuyên bố mất tích; "
        "Biệt tích hơn 3 năm và đã đăng tìm kiếm."
    ),
    params_schema=LyHonKhiMatTichHoacKhongLienLacParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
