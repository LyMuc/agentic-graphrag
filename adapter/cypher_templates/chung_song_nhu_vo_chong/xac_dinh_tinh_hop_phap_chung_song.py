"""Template — xác định tính hợp pháp chung sống (Đ5 K2Đc, Đ14 K1)."""
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

_ROUTER_FIELDS = ("khia_canh_hop_phap",)
_DIEU_5_14_WHITELIST = [
    "Luat_HNGD_2014_Dieu_5",
    "Luat_HNGD_2014_Dieu_14",
]


class XacDinhTinhHopPhapChungSongParams(BaseModel):
    tinh_trang_hon_nhan_cac_ben: Literal[
        "ca_hai_chua_co_vo_chong",
        "mot_ben_dang_co_vo_chong",
        "khong_ro",
    ] = Field(
        description=(
            "Đang có vợ/chồng/đã có gia đình -> mot_ben_dang_co_vo_chong; "
            "chỉ bạn trai/bạn gái -> khong_ro; cả hai độc thân -> ca_hai_chua_co_vo_chong."
        )
    )
    khia_canh_hop_phap: Literal[
        "co_vi_pham_hay_khong",
        "truong_hop_bi_cam",
        "phan_biet_bi_cam_va_khong_dang_ky",
        "tong_quat",
    ] = Field(
        description=(
            "Có vi phạm/bị cấm -> co_vi_pham_hay_khong; trường hợp bị cấm "
            "-> truong_hop_bi_cam; phân biệt sống thử -> phan_biet_bi_cam_va_khong_dang_ky."
        )
    )


_SEED_BODY = f"""
WITH $tt AS tt, $kc AS kc, $whitelist_dieu_ids AS wl

MATCH (hv:HanhVi:{TOPIC_LABEL} {{id: 'chung_song_nhu_vo_chong_khong_dang_ky', topic: '{TOPIC}'}})

OPTIONAL MATCH (dk_cam:DieuKien:{TOPIC_LABEL} {{id: 'mot_ben_dang_co_vo_hoac_chong', topic: '{TOPIC}'}})
WHERE tt IN ['mot_ben_dang_co_vo_chong', 'khong_ro'] OR kc IN ['truong_hop_bi_cam', 'phan_biet_bi_cam_va_khong_dang_ky', 'tong_quat']
OPTIONAL MATCH (hv_cam:HanhVi:{TOPIC_LABEL} {{id: 'chung_song_voi_nguoi_dang_co_vo_chong', topic: '{TOPIC}'}})
WHERE dk_cam IS NOT NULL

OPTIONAL MATCH (dk_dk:DieuKien:{TOPIC_LABEL} {{id: 'du_dieu_kien_ket_hon', topic: '{TOPIC}'}})
WHERE tt IN ['ca_hai_chua_co_vo_chong', 'khong_ro']
OPTIONAL MATCH (dk_kdk:DieuKien:{TOPIC_LABEL} {{id: 'khong_dang_ky_ket_hon', topic: '{TOPIC}'}})
WHERE tt IN ['ca_hai_chua_co_vo_chong', 'khong_ro']
OPTIONAL MATCH (hq:HauQua:{TOPIC_LABEL} {{id: 'khong_phat_sinh_quyen_nghia_vu_vo_chong', topic: '{TOPIC}'}})
WHERE tt = 'ca_hai_chua_co_vo_chong'

WITH wl, tt, kc,
  [x IN collect(DISTINCT hv) + collect(DISTINCT dk_cam) + collect(DISTINCT hv_cam)
       + collect(DISTINCT dk_dk) + collect(DISTINCT dk_kdk) + collect(DISTINCT hq)
   WHERE x IS NOT NULL] AS seed_nodes,
  CASE tt
    WHEN 'mot_ben_dang_co_vo_chong' THEN
      [x IN collect(DISTINCT dk_cam) + collect(DISTINCT hv_cam) WHERE x IS NOT NULL]
    WHEN 'ca_hai_chua_co_vo_chong' THEN
      [x IN collect(DISTINCT dk_dk) + collect(DISTINCT dk_kdk) + collect(DISTINCT hq)
       WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT dk_cam) + collect(DISTINCT hv_cam)
           + collect(DISTINCT dk_dk) + collect(DISTINCT dk_kdk)
       WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: XacDinhTinhHopPhapChungSongParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "tt": params.tinh_trang_hon_nhan_cac_ben,
        "kc": params.khia_canh_hop_phap,
        "whitelist_dieu_ids": _DIEU_5_14_WHITELIST if use_wl else [],
    }


xac_dinh_tinh_hop_phap_chung_song = CypherTemplate(
    name="xac_dinh_tinh_hop_phap_chung_song",
    description=(
        "Xác định việc chung sống như vợ chồng không đăng ký có bị cấm không, "
        "trọng tâm một bên đang có vợ/chồng (Đ5 K2Đc). Không kết luận mọi "
        "'sống thử' đều vi phạm. "
        "Ví dụ: Bạn trai rủ dọn ra sống chung như vợ chồng có vi phạm pháp luật không?"
    ),
    params_schema=XacDinhTinhHopPhapChungSongParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
