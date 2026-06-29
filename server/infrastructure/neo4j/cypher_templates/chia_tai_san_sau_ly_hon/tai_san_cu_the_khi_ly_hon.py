"""Template 2 — TÀI SẢN CỤ THỂ KHI LY HÔN (seed Đ59).

Coverage feat_llm stt: 5,13,21,22,23,24,25,28,30.
Seed kiểu semantic graph: DAN_TOI + TAC_DONG_LEN theo nguồn gốc/loại tài sản.
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

_ROUTER_FIELDS = ("loai_tai_san", "nguon_goc")
_DIEU_59_WHITELIST = ["Luat_HNGD_2014_Dieu_59"]

# Map param loai_tai_san → id LoaiTaiSan trong KG (Phase B).
_LOAI_TS_TO_LTS: dict[str, str] = {
    "nha_mua_tra_gop": "bat_dong_san_chung",
    "bat_dong_san": "bat_dong_san_chung",
    "quyen_su_dung_dat": "qsd_dat_la_tai_san_chung",
    "tai_khoan_tiet_kiem_tro_cap": "tai_khoan_tiet_kiem_tro_cap_chung",
    "tai_san_duoc_tang_cho_ngay_cuoi": "tai_san_duoc_tang_cho",
    "dong_san_phai_dang_ky": "dong_san_phai_dang_ky_chung",
    "tai_san_chung": "bat_dong_san_chung",
    "tai_san_rieng": "bat_dong_san_rieng",
}


class TaiSanCuTheKhiLyHonParams(BaseModel):
    loai_tai_san: Literal[
        "nha_mua_tra_gop",
        "bat_dong_san",
        "quyen_su_dung_dat",
        "tai_khoan_tiet_kiem_tro_cap",
        "tai_san_duoc_tang_cho_ngay_cuoi",
        "dong_san_phai_dang_ky",
        "tai_san_chung",
        "tai_san_rieng",
        "khac",
        "khong_ro",
    ] = Field(
        default="khong_ro",
        description=(
            "Loại tài sản cụ thể. Map: 'nhà trả góp'→nha_mua_tra_gop; "
            "'nhà/nhà đất'→bat_dong_san; 'đất/sổ đỏ'→quyen_su_dung_dat; "
            "'trợ cấp/sổ tiết kiệm'→tai_khoan_tiet_kiem_tro_cap; "
            "'cho ngày cưới'→tai_san_duoc_tang_cho_ngay_cuoi; "
            "'ô tô/xe'→dong_san_phai_dang_ky."
        ),
    )
    nguon_goc: Literal[
        "tra_gop",
        "tang_cho",
        "tang_cho_rieng",
        "trong_hon_nhan",
        "truoc_hon_nhan",
        "dung_ten_mot_ben",
        "ly_than",
        "da_chia_sau_ly_hon",
        "khong_ro",
    ] = Field(
        default="khong_ro",
        description=(
            "Nguồn gốc tài sản. Map: 'trả góp'→tra_gop; 'bố mẹ cho'→tang_cho; "
            "'cho riêng'→tang_cho_rieng; 'đứng tên một bên'→dung_ten_mot_ben; "
            "'ly thân'→ly_than; 'đã trả nửa/đã chia'→da_chia_sau_ly_hon."
        ),
    )
    tinh_chat_du_kien: Literal["chung", "rieng", "chua_ro"] = Field(
        default="chua_ro",
        description="Tính chất dự kiến nếu câu hỏi nói rõ chung/riêng.",
    )
    da_chia_va_thanh_toan: Literal["co", "khong", "khong_ro"] = Field(
        default="khong_ro",
        description="Map 'đã trả nửa/đã thanh toán/đã chia xong'→co.",
    )


_SEED_BODY = f"""
// ============================================================
// PHẦN 1 — SEED semantic graph (tài sản cụ thể khi ly hôn)
// ============================================================
WITH $loai_tai_san AS lts_param,
     $nguon_goc AS ng,
     $tinh_chat_du_kien AS tc,
     $da_chia_va_thanh_toan AS dctt,
     $asset_lts_id AS asset_id,
     $whitelist_dieu_ids AS wl

WITH wl, lts_param, ng, tc, dctt, asset_id,
  ng IN ['tang_cho_rieng', 'truoc_hon_nhan'] OR tc = 'rieng' AS nhanh_rieng,
  ng IN ['tra_gop', 'trong_hon_nhan'] OR lts_param IN ['nha_mua_tra_gop', 'tai_san_chung']
    OR tc = 'chung' AS nhanh_chung

OPTIONAL MATCH (giai:HanhVi:{TOPIC_LABEL} {{id: 'giai_quyet_tai_san_khi_ly_hon', topic: '{TOPIC}'}})
WHERE dctt = 'co' OR lts_param = 'khong_ro'

OPTIONAL MATCH (chia:HanhVi:{TOPIC_LABEL} {{id: 'chia_tai_san_chung_khi_ly_hon', topic: '{TOPIC}'}})
WHERE nhanh_chung OR lts_param IN ['nha_mua_tra_gop', 'bat_dong_san', 'tai_san_chung', 'khong_ro']

OPTIONAL MATCH (chia)-[:DAN_TOI]->(hv:HanhVi:{TOPIC_LABEL} {{id: 'chia_bang_hien_vat'}})
WHERE ng = 'tra_gop' OR lts_param = 'nha_mua_tra_gop'
OPTIONAL MATCH (hv)-[:DAN_TOI]->(hq_tt:HauQua:{TOPIC_LABEL} {{id: 'thanh_toan_chenh_lech_gia_tri'}})
WHERE ng = 'tra_gop' OR lts_param = 'nha_mua_tra_gop' OR dctt = 'co'

OPTIONAL MATCH (xac:HanhVi:{TOPIC_LABEL} {{id: 'xac_dinh_tai_san_rieng_khi_ly_hon', topic: '{TOPIC}'}})
WHERE nhanh_rieng OR lts_param IN ['tai_san_rieng', 'tai_san_duoc_tang_cho_ngay_cuoi']
OPTIONAL MATCH (xac)-[:DAN_TOI]->(hq_rieng:HauQua:{TOPIC_LABEL} {{id: 'chia_gia_tri_tai_san_rieng_da_sap_nhap'}})
WHERE nhanh_rieng

OPTIONAL MATCH (chia)-[:TAC_DONG_LEN]->(lts_chung:LoaiTaiSan:{TOPIC_LABEL})
WHERE asset_id IS NOT NULL AND nhanh_chung
  AND (lts_chung.id = asset_id OR lts_chung.tinh_chat = 'chung')

OPTIONAL MATCH (xac)-[:TAC_DONG_LEN]->(lts_rieng:LoaiTaiSan:{TOPIC_LABEL})
WHERE asset_id IS NOT NULL AND nhanh_rieng
  AND (lts_rieng.id = asset_id OR lts_rieng.tinh_chat = 'rieng')

WITH wl, lts_param, dctt, nhanh_rieng, nhanh_chung,
  collect(DISTINCT giai) AS c_giai,
  collect(DISTINCT chia) AS c_chia,
  collect(DISTINCT hv) AS c_hv,
  collect(DISTINCT hq_tt) AS c_hq_tt,
  collect(DISTINCT xac) AS c_xac,
  collect(DISTINCT hq_rieng) AS c_hq_rieng,
  collect(DISTINCT lts_chung) AS c_lts_chung,
  collect(DISTINCT lts_rieng) AS c_lts_rieng

WITH wl, lts_param, dctt,
  size([x IN c_xac + c_hq_rieng + c_lts_rieng WHERE x IS NOT NULL]) > 0 AS has_rieng_leaf,
  size([x IN c_chia + c_hv + c_hq_tt + c_lts_chung WHERE x IS NOT NULL]) > 0 AS has_chung_leaf,
  c_giai, c_chia, c_hv, c_hq_tt, c_xac, c_hq_rieng, c_lts_chung, c_lts_rieng

WITH wl, lts_param, dctt, has_rieng_leaf, has_chung_leaf,
  c_giai, c_chia, c_hv, c_hq_tt, c_xac, c_hq_rieng, c_lts_chung, c_lts_rieng,
  [x IN c_giai + c_chia + c_hv + c_hq_tt + c_xac + c_hq_rieng
       + c_lts_chung + c_lts_rieng WHERE x IS NOT NULL] AS seed_nodes,
  CASE
    WHEN has_rieng_leaf THEN
      [x IN c_xac + c_hq_rieng + c_lts_rieng WHERE x IS NOT NULL]
    WHEN has_chung_leaf THEN
      [x IN c_chia + c_hv + c_hq_tt + c_lts_chung WHERE x IS NOT NULL]
    WHEN dctt = 'co' OR lts_param = 'khong_ro' THEN
      [x IN c_giai + c_chia + c_hv + c_hq_tt + c_xac + c_hq_rieng
           + c_lts_chung + c_lts_rieng WHERE x IS NOT NULL]
    ELSE
      [x IN c_chia + c_xac WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: TaiSanCuTheKhiLyHonParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    asset_id = _LOAI_TS_TO_LTS.get(params.loai_tai_san)
    return {
        "asset_lts_id": asset_id,
        "whitelist_dieu_ids": _DIEU_59_WHITELIST if use_wl else [],
        **params.model_dump(),
    }


tai_san_cu_the_khi_ly_hon = CypherTemplate(
    name="tai_san_cu_the_khi_ly_hon",
    description=(
        "Chia/xác định tài sản cụ thể khi ly hôn (nhà, đất, xe, trả góp, tặng cho, "
        "tài sản chung/riêng, thanh toán chênh lệch). Phù hợp khi câu hỏi nêu loại "
        "tài sản hoặc nguồn gốc cụ thể kèm 'khi ly hôn/chia tài sản'."
    ),
    params_schema=TaiSanCuTheKhiLyHonParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
