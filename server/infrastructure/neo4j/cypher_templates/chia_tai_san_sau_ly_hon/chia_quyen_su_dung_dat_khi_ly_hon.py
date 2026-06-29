"""Template 4 — CHIA QUYỀN SỬ DỤNG ĐẤT KHI LY HÔN (Đ62).

Coverage feat_llm stt: 14,15,16,17.
Seed kiểu semantic graph: TAC_DONG_LEN + AP_DUNG_KHI trên LoaiTaiSan.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from server.infrastructure.neo4j.cypher_templates import CypherTemplate
from server.infrastructure.neo4j.cypher_templates.chia_tai_san_sau_ly_hon._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("tinh_chat_qsd_dat", "hanh_vi_context")
_DIEU_62_WHITELIST = ["Luat_HNGD_2014_Dieu_62"]


class ChiaQuyenSuDungDatParams(BaseModel):
    tinh_chat_qsd_dat: Literal["chung", "rieng", "khong_ro"] = Field(
        default="khong_ro",
        description="Map 'tài sản chung'→chung; 'tài sản riêng'→rieng.",
    )
    loai_dat: Literal[
        "dat_nong_nghiep_hang_nam_nuoi_trong_thuy_san",
        "dat_cay_lau_nam_dat_lam_nghiep_dat_o",
        "loai_dat_khac",
        "khong_ro",
    ] = Field(default="khong_ro")
    ho_gia_dinh: Literal["co", "khong", "khong_ro"] = Field(default="khong_ro")
    nhu_cau_su_dung: Literal["ca_hai", "mot_ben", "khong_ro"] = Field(default="khong_ro")
    hanh_vi_context: Literal[
        "mua_dat_giau_vo", "dung_ten_mot_ben", "tong_quat", "khong_ro"
    ] = Field(default="khong_ro")


_SEED_BODY = f"""
// ============================================================
// PHẦN 1 — SEED semantic graph (QSDĐ khi ly hôn — Đ62)
// ============================================================
WITH $tinh_chat_qsd_dat AS tc_param,
     $loai_dat AS ld,
     $ho_gia_dinh AS hgd,
     $nhu_cau_su_dung AS ncsd,
     $whitelist_dieu_ids AS wl

WITH wl, tc_param, ld, hgd, ncsd,
  CASE tc_param
    WHEN 'rieng' THEN ['rieng']
    WHEN 'chung' THEN ['chung']
    ELSE ['chung', 'rieng']
  END AS tc_list

MATCH (anchor:HanhVi:{TOPIC_LABEL} {{id: 'chia_quyen_su_dung_dat_khi_ly_hon', topic: '{TOPIC}'}})

UNWIND tc_list AS tc

OPTIONAL MATCH (anchor)-[:TAC_DONG_LEN]->(lts:LoaiTaiSan:{TOPIC_LABEL})
WHERE lts.tinh_chat = tc

OPTIONAL MATCH (lts)-[:AP_DUNG_KHI]->(sub:LoaiTaiSan:{TOPIC_LABEL})
WHERE lts.id = 'qsd_dat_la_tai_san_chung'
  AND (
    ld = 'khong_ro'
    OR sub.id = ld
    OR (ld = 'dat_nong_nghiep_hang_nam_nuoi_trong_thuy_san'
        AND sub.id = 'dat_nong_nghiep_hang_nam_nuoi_trong_thuy_san')
    OR (ld = 'dat_cay_lau_nam_dat_lam_nghiep_dat_o'
        AND sub.id = 'dat_cay_lau_nam_dat_lam_nghiep_dat_o')
    OR (ld = 'loai_dat_khac' AND sub.id = 'loai_dat_khac')
  )
  AND (hgd = 'khong_ro' OR hgd = 'khong'
       OR sub.id = 'qsd_dat_chung_voi_ho_gia_dinh')

OPTIONAL MATCH (hq:HauQua:{TOPIC_LABEL} {{id: 'giai_quyet_quyen_loi_ben_khong_co_qsd_dat', topic: '{TOPIC}'}})
WHERE ncsd = 'mot_ben'

WITH wl, tc_param,
  collect(DISTINCT anchor) AS anchors,
  collect(DISTINCT lts) AS lts_list,
  collect(DISTINCT sub) AS sub_list,
  collect(DISTINCT hq) AS hq_list

WITH wl, tc_param,
  [x IN anchors + lts_list + sub_list + hq_list WHERE x IS NOT NULL] AS seed_nodes,
  CASE
    WHEN tc_param IN ['rieng', 'chung']
         AND size([x IN lts_list WHERE x IS NOT NULL]) > 0 THEN
      [x IN lts_list + sub_list + hq_list WHERE x IS NOT NULL]
    ELSE
      [x IN anchors + lts_list + sub_list + hq_list WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: ChiaQuyenSuDungDatParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "whitelist_dieu_ids": _DIEU_62_WHITELIST if use_wl else [],
        **params.model_dump(),
    }


chia_quyen_su_dung_dat_khi_ly_hon = CypherTemplate(
    name="chia_quyen_su_dung_dat_khi_ly_hon",
    description=(
        "Chia quyền sử dụng đất khi ly hôn (Đ62): QSDĐ là tài sản riêng/chung, "
        "đất nông nghiệp, đất ở, đất chung hộ gia đình, quyền lợi bên không có "
        "QSDĐ, 'mua đất giấu vợ'. Phù hợp khi câu hỏi có 'quyền sử dụng đất', "
        "'đất', 'sổ đỏ', 'mua đất' và hỏi chia khi ly hôn."
    ),
    params_schema=ChiaQuyenSuDungDatParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
