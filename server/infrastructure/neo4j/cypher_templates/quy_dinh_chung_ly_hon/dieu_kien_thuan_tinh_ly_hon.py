"""Template — điều kiện thuận tình ly hôn (Đ55)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from server.infrastructure.neo4j.cypher_templates import CypherTemplate
from server.infrastructure.neo4j.cypher_templates.quy_dinh_chung_ly_hon._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("khia_canh_thuan_tinh",)
_DIEU_55_WHITELIST = ["Luat_HNGD_2014_Dieu_55"]


class DieuKienThuanTinhLyHonParams(BaseModel):
    muc_do_thoa_thuan: Literal[
        "day_du",
        "khong_thoa_thuan_duoc",
        "thoa_thuan_khong_bao_dam",
        "khong_ro",
    ] = Field(
        description=(
            "Đã thống nhất hết → day_du; không thỏa thuận được → khong_thoa_thuan_duoc; "
            "thỏa thuận bất lợi vợ/con → thoa_thuan_khong_bao_dam."
        )
    )
    noi_dung_thoa_thuan: Literal[
        "tai_san", "con_chung", "ca_tai_san_va_con", "khong_ro"
    ] = Field(
        description="Chỉ tài sản → tai_san; chỉ con → con_chung; cả hai → ca_tai_san_va_con."
    )
    tu_nguyen: Literal["co", "khong", "khong_ro"] = Field(
        description="Hai bên tự nguyện → co; bị ép → khong."
    )
    khia_canh_thuan_tinh: Literal[
        "khai_niem",
        "dieu_kien_cong_nhan",
        "hau_qua_khong_dat_dieu_kien",
        "tong_quat",
    ] = Field(
        description=(
            "Là gì → khai_niem; điều kiện/khi nào công nhận → dieu_kien_cong_nhan; "
            "không đạt điều kiện → hau_qua_khong_dat_dieu_kien."
        )
    )


_SEED_BODY = f"""
WITH $kc AS kc, $nd AS nd, $muc AS muc, $whitelist_dieu_ids AS wl

MATCH (ht:HinhThucLyHon:{TOPIC_LABEL} {{id: 'thuan_tinh_ly_hon', topic: '{TOPIC}'}})
OPTIONAL MATCH (hv:HanhVi:{TOPIC_LABEL} {{id: 'cung_yeu_cau_ly_hon', topic: '{TOPIC}'}})

OPTIONAL MATCH (dk_tn:DieuKien:{TOPIC_LABEL} {{id: 'hai_ben_that_su_tu_nguyen_ly_hon', topic: '{TOPIC}'}})
WHERE kc IN ['khai_niem', 'dieu_kien_cong_nhan', 'tong_quat']

OPTIONAL MATCH (tt_ts:ThoaThuan:{TOPIC_LABEL} {{id: 'thoa_thuan_chia_tai_san_khi_thuan_tinh', topic: '{TOPIC}'}})
WHERE nd IN ['tai_san', 'ca_tai_san_va_con', 'khong_ro']
OPTIONAL MATCH (dk_ts:DieuKien:{TOPIC_LABEL} {{id: 'da_thoa_thuan_ve_chia_tai_san', topic: '{TOPIC}'}})
WHERE tt_ts IS NOT NULL

OPTIONAL MATCH (tt_con:ThoaThuan:{TOPIC_LABEL} {{id: 'thoa_thuan_viec_trong_nom_nuoi_duong_cham_soc_giao_duc_con', topic: '{TOPIC}'}})
WHERE nd IN ['con_chung', 'ca_tai_san_va_con', 'khong_ro']
OPTIONAL MATCH (dk_con:DieuKien:{TOPIC_LABEL} {{id: 'da_thoa_thuan_ve_viec_con', topic: '{TOPIC}'}})
WHERE tt_con IS NOT NULL

OPTIONAL MATCH (tt_q:ThoaThuan:{TOPIC_LABEL} {{id: 'thoa_thuan_bao_dam_quyen_loi_chinh_dang_cua_vo_va_con', topic: '{TOPIC}'}})
WHERE nd IN ['ca_tai_san_va_con', 'khong_ro']
OPTIONAL MATCH (dk_q:DieuKien:{TOPIC_LABEL} {{id: 'thoa_thuan_bao_dam_quyen_loi_vo_va_con', topic: '{TOPIC}'}})
WHERE tt_q IS NOT NULL

OPTIONAL MATCH (dk_ktt:DieuKien:{TOPIC_LABEL} {{id: 'khong_thoa_thuan_duoc_ve_tai_san_hoac_con', topic: '{TOPIC}'}})
WHERE muc = 'khong_thoa_thuan_duoc' OR kc = 'hau_qua_khong_dat_dieu_kien'
OPTIONAL MATCH (hq_ktt:HauQua:{TOPIC_LABEL} {{id: 'toa_an_giai_quyet_ly_hon_khi_thoa_thuan_khong_dat', topic: '{TOPIC}'}})
WHERE dk_ktt IS NOT NULL

OPTIONAL MATCH (dk_tkb:DieuKien:{TOPIC_LABEL} {{id: 'thoa_thuan_khong_bao_dam_quyen_loi_vo_va_con', topic: '{TOPIC}'}})
WHERE muc = 'thoa_thuan_khong_bao_dam'
OPTIONAL MATCH (hq_tkb:HauQua:{TOPIC_LABEL} {{id: 'toa_an_giai_quyet_ly_hon_khi_thoa_thuan_khong_dat', topic: '{TOPIC}'}})
WHERE dk_tkb IS NOT NULL

OPTIONAL MATCH (hq_cn:HauQua:{TOPIC_LABEL} {{id: 'toa_an_cong_nhan_thuan_tinh_ly_hon', topic: '{TOPIC}'}})
WHERE kc IN ['dieu_kien_cong_nhan', 'khai_niem', 'tong_quat']

WITH wl, kc,
  [x IN collect(DISTINCT ht) + collect(DISTINCT hv) + collect(DISTINCT dk_tn)
       + collect(DISTINCT tt_ts) + collect(DISTINCT dk_ts)
       + collect(DISTINCT tt_con) + collect(DISTINCT dk_con)
       + collect(DISTINCT tt_q) + collect(DISTINCT dk_q)
       + collect(DISTINCT dk_ktt) + collect(DISTINCT hq_ktt)
       + collect(DISTINCT dk_tkb) + collect(DISTINCT hq_tkb)
       + collect(DISTINCT hq_cn)
   WHERE x IS NOT NULL] AS seed_nodes,
  CASE kc
    WHEN 'hau_qua_khong_dat_dieu_kien' THEN
      [x IN collect(DISTINCT dk_ktt) + collect(DISTINCT hq_ktt)
           + collect(DISTINCT dk_tkb) + collect(DISTINCT hq_tkb)
       WHERE x IS NOT NULL]
    WHEN 'dieu_kien_cong_nhan' THEN
      [x IN collect(DISTINCT dk_tn) + collect(DISTINCT dk_ts) + collect(DISTINCT dk_con)
           + collect(DISTINCT dk_q) + collect(DISTINCT hq_cn)
       WHERE x IS NOT NULL]
    WHEN 'khai_niem' THEN
      [x IN collect(DISTINCT ht) + collect(DISTINCT hv) + collect(DISTINCT dk_tn)
       WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT ht) + collect(DISTINCT hq_cn) WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: DieuKienThuanTinhLyHonParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "kc": params.khia_canh_thuan_tinh,
        "nd": params.noi_dung_thoa_thuan,
        "muc": params.muc_do_thoa_thuan,
        "whitelist_dieu_ids": _DIEU_55_WHITELIST if use_wl else [],
    }


dieu_kien_thuan_tinh_ly_hon = CypherTemplate(
    name="dieu_kien_thuan_tinh_ly_hon",
    description=(
        "Khái niệm, điều kiện công nhận thuận tình ly hôn và hậu quả khi thỏa thuận "
        "không đạt yêu cầu (Đ55). Chỉ đánh giá điều kiện, không truy xuất chi tiết "
        "chia tài sản hoặc giao con. "
        "Ví dụ: Điều kiện để Tòa án công nhận thuận tình ly hôn là gì; "
        "Khi nào Tòa án công nhận thuận tình ly hôn; "
        "Thế nào được coi là thuận tình ly hôn."
    ),
    params_schema=DieuKienThuanTinhLyHonParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
