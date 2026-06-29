"""Template — thời điểm chấm dứt hôn nhân (Đ57, bổ trợ Đ3, Đ65)."""
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

_ROUTER_FIELDS = ("tinh_huong",)
_DIEU_57_WHITELIST = ["Luat_HNGD_2014_Dieu_57"]
_DIEU_65_WHITELIST = ["Luat_HNGD_2014_Dieu_65"]
_DIEU_3_WHITELIST = ["Luat_HNGD_2014_Dieu_3_Khoan_14"]
_DIEU_19_WHITELIST = ["Luat_HNGD_2014_Dieu_19"]


class ThoiDiemChamDutHonNhanParams(BaseModel):
    tinh_huong: Literal[
        "ban_an_quyet_dinh_co_hieu_luc",
        "dang_lam_thu_tuc",
        "ly_than",
        "xe_giay_dang_ky_ket_hon",
        "vo_chong_chet",
        "tong_quat",
    ] = Field(
        description=(
            "Bản án có hiệu lực → ban_an_quyet_dinh_co_hieu_luc; đang làm thủ tục "
            "→ dang_lam_thu_tuc; ly thân → ly_than; xé giấy kết hôn "
            "→ xe_giay_dang_ky_ket_hon; vợ/chồng chết → vo_chong_chet."
        )
    )
    khia_canh_cham_dut: Literal[
        "thoi_diem_cham_dut",
        "quan_he_hon_nhan_con_ton_tai",
        "trach_nhiem_gui_ban_an",
        "tong_quat",
    ] = Field(
        description=(
            "Khi nào chấm dứt → thoi_diem_cham_dut; hôn nhân còn tồn tại "
            "→ quan_he_hon_nhan_con_ton_tai; Tòa gửi quyết định → trach_nhiem_gui_ban_an."
        )
    )
    hanh_vi_trong_khi_cho: Literal["chung_song_voi_nguoi_khac", "khong_ro"] = Field(
        description="Chung sống với người khác khi đang chờ ly hôn."
    )


_SEED_BODY = f"""
WITH $th AS th, $kc AS kc, $hanh_vi AS hv, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (hq_ba:HauQua:{TOPIC_LABEL} {{id: 'quan_he_hon_nhan_cham_dut_khi_ban_an_co_hieu_luc', topic: '{TOPIC}'}})
WHERE th IN ['ban_an_quyet_dinh_co_hieu_luc', 'tong_quat']
OPTIONAL MATCH (tthn_cd:TinhTrangHonNhan:{TOPIC_LABEL} {{id: 'hon_nhan_da_cham_dut_do_ly_hon', topic: '{TOPIC}'}})
WHERE hq_ba IS NOT NULL

OPTIONAL MATCH (hq_dt:HauQua:{TOPIC_LABEL} {{id: 'dang_lam_thu_tuc_hon_nhan_van_ton_tai', topic: '{TOPIC}'}})
WHERE th IN ['dang_lam_thu_tuc', 'tong_quat']
OPTIONAL MATCH (tthn_tt:TinhTrangHonNhan:{TOPIC_LABEL} {{id: 'hon_nhan_dang_ton_tai', topic: '{TOPIC}'}})
WHERE hq_dt IS NOT NULL

OPTIONAL MATCH (hv_lt:HanhVi:{TOPIC_LABEL} {{id: 'ly_than_khi_chua_co_ban_an_ly_hon', topic: '{TOPIC}'}})
WHERE th = 'ly_than'
OPTIONAL MATCH (hq_lt:HauQua:{TOPIC_LABEL} {{id: 'ly_than_khong_tu_cham_dut_hon_nhan', topic: '{TOPIC}'}})
WHERE th = 'ly_than'

OPTIONAL MATCH (hv_xe:HanhVi:{TOPIC_LABEL} {{id: 'xe_giay_dang_ky_ket_hon', topic: '{TOPIC}'}})
WHERE th = 'xe_giay_dang_ky_ket_hon'
OPTIONAL MATCH (hq_xe:HauQua:{TOPIC_LABEL} {{id: 'xe_giay_khong_tu_cham_dut_hon_nhan', topic: '{TOPIC}'}})
WHERE th = 'xe_giay_dang_ky_ket_hon'

OPTIONAL MATCH (tthn_chet:TinhTrangHonNhan:{TOPIC_LABEL} {{id: 'hon_nhan_cham_dut_do_vo_chong_chet', topic: '{TOPIC}'}})
WHERE th IN ['vo_chong_chet', 'tong_quat']

OPTIONAL MATCH (hv_cs:HanhVi:{TOPIC_LABEL} {{id: 'chung_song_voi_nguoi_khac_khi_hon_nhan_chua_cham_dut', topic: '{TOPIC}'}})
WHERE hv = 'chung_song_voi_nguoi_khac'
OPTIONAL MATCH (nv:NghiaVu:{TOPIC_LABEL} {{id: 'nghia_vu_chung_thuy', topic: '{TOPIC}'}})
WHERE hv_cs IS NOT NULL

OPTIONAL MATCH (hv_gui:HanhVi:{TOPIC_LABEL} {{id: 'toa_an_gui_ban_an_quyet_dinh_ly_hon', topic: '{TOPIC}'}})
WHERE kc = 'trach_nhiem_gui_ban_an'
OPTIONAL MATCH (hq_gui:HauQua:{TOPIC_LABEL} {{id: 'ban_an_duoc_gui_cho_co_quan_va_cac_ben', topic: '{TOPIC}'}})
WHERE hv_gui IS NOT NULL

WITH wl, th, kc,
  [x IN collect(DISTINCT hq_ba) + collect(DISTINCT tthn_cd)
       + collect(DISTINCT hq_dt) + collect(DISTINCT tthn_tt)
       + collect(DISTINCT hv_lt) + collect(DISTINCT hq_lt)
       + collect(DISTINCT hv_xe) + collect(DISTINCT hq_xe)
       + collect(DISTINCT tthn_chet)
       + collect(DISTINCT hv_cs) + collect(DISTINCT nv)
       + collect(DISTINCT hv_gui) + collect(DISTINCT hq_gui)
   WHERE x IS NOT NULL] AS seed_nodes,
  CASE th
    WHEN 'ban_an_quyet_dinh_co_hieu_luc' THEN
      [x IN collect(DISTINCT hq_ba) + collect(DISTINCT tthn_cd) WHERE x IS NOT NULL]
    WHEN 'dang_lam_thu_tuc' THEN
      [x IN collect(DISTINCT hq_dt) + collect(DISTINCT tthn_tt)
           + collect(DISTINCT hv_cs) + collect(DISTINCT nv)
       WHERE x IS NOT NULL]
    WHEN 'ly_than' THEN
      [x IN collect(DISTINCT hv_lt) + collect(DISTINCT hq_lt) + collect(DISTINCT tthn_tt)
       WHERE x IS NOT NULL]
    WHEN 'xe_giay_dang_ky_ket_hon' THEN
      [x IN collect(DISTINCT hv_xe) + collect(DISTINCT hq_xe) + collect(DISTINCT tthn_tt)
       WHERE x IS NOT NULL]
    WHEN 'vo_chong_chet' THEN
      [x IN collect(DISTINCT tthn_chet) WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT hq_ba) + collect(DISTINCT tthn_chet) WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: ThoiDiemChamDutHonNhanParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    whitelist: list[str] = []
    if use_wl:
        whitelist.extend(_DIEU_57_WHITELIST)
        if params.tinh_huong == "tong_quat":
            whitelist.extend(_DIEU_65_WHITELIST)
    if params.tinh_huong in ("xe_giay_dang_ky_ket_hon", "tong_quat"):
        whitelist.extend(_DIEU_3_WHITELIST)
    if params.tinh_huong == "vo_chong_chet":
        whitelist = _DIEU_65_WHITELIST if use_wl else []
    if params.hanh_vi_trong_khi_cho == "chung_song_voi_nguoi_khac":
        whitelist.extend(_DIEU_19_WHITELIST)
    return {
        "th": params.tinh_huong,
        "kc": params.khia_canh_cham_dut,
        "hanh_vi": params.hanh_vi_trong_khi_cho,
        "whitelist_dieu_ids": list(dict.fromkeys(whitelist)),
    }


thoi_diem_cham_dut_hon_nhan = CypherTemplate(
    name="thoi_diem_cham_dut_hon_nhan",
    description=(
        "Quan hệ hôn nhân chỉ chấm dứt khi bản án/quyết định ly hôn có hiệu lực (Đ57). "
        "Xử lý ngộ nhận ly thân, đang làm thủ tục, xé giấy kết hôn; có thể seed Đ65 "
        "khi hỏi chấm dứt hôn nhân nói chung. "
        "Ví dụ: Chung sống với người khác khi đang làm thủ tục ly hôn; "
        "Thời điểm chấm dứt hôn nhân; "
        "Ly thân có chấm dứt hôn nhân không; "
        "Xé giấy đăng ký kết hôn có chấm dứt hôn nhân không."
    ),
    params_schema=ThoiDiemChamDutHonNhanParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
