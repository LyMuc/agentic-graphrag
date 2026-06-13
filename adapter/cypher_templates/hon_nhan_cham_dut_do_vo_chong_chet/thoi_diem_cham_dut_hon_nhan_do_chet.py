"""Template — thời điểm chấm dứt hôn nhân do chết/tuyên bố đã chết (Đ65)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.hon_nhan_cham_dut_do_vo_chong_chet._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("can_cu_cham_dut",)
_DIEU_65_WHITELIST = ["Luat_HNGD_2014_Dieu_65"]


class ThoiDiemChamDutHonNhanDoChetParams(BaseModel):
    can_cu_cham_dut: Literal[
        "chet_thuc_te",
        "bi_tuyen_bo_da_chet",
        "biet_tich_chua_co_tuyen_bo",
        "tong_quat",
        "khong_ro",
    ] = Field(
        description=(
            "chết/mất → chet_thuc_te; Tòa tuyên bố đã chết → bi_tuyen_bo_da_chet; "
            "chỉ biệt tích/mất liên lạc → biet_tich_chua_co_tuyen_bo; hỏi chung → tong_quat."
        )
    )
    khia_canh_thoi_diem: Literal[
        "co_cham_dut_hay_khong",
        "thoi_diem_cham_dut",
        "co_duoc_ket_hon_voi_nguoi_khac",
        "dieu_kien_tuyen_bo_da_chet",
        "tong_quat",
    ] = Field(
        description=(
            "có chấm dứt không → co_cham_dut_hay_khong; khi nào → thoi_diem_cham_dut; "
            "kết hôn người mới → co_duoc_ket_hon_voi_nguoi_khac; "
            "bao nhiêu năm biệt tích → dieu_kien_tuyen_bo_da_chet."
        )
    )
    chu_the_xay_ra_su_kien: Literal["vo", "chong", "mot_ben", "khong_ro"] = Field(
        description="Chủ thể chết/biệt tích/bị tuyên bố đã chết."
    )


_SEED_BODY = f"""
WITH $cc AS cc, $kc AS kc, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (dk_ct:DieuKien:{TOPIC_LABEL} {{id: 'mot_ben_chet_thuc_te', topic: '{TOPIC}'}})
WHERE cc IN ['chet_thuc_te', 'tong_quat', 'khong_ro']
OPTIONAL MATCH (hq_ct:HauQua:{TOPIC_LABEL} {{id: 'hon_nhan_cham_dut_tai_thoi_diem_vo_hoac_chong_chet', topic: '{TOPIC}'}})
WHERE dk_ct IS NOT NULL
OPTIONAL MATCH (tthn_ct:TinhTrangHonNhan:{TOPIC_LABEL} {{id: 'hon_nhan_cham_dut_do_mot_ben_chet_hoac_bi_tuyen_bo_da_chet', topic: '{TOPIC}'}})
WHERE hq_ct IS NOT NULL

OPTIONAL MATCH (qt_tb:QuyTrinhPhapLy:{TOPIC_LABEL} {{id: 'toa_an_tuyen_bo_vo_hoac_chong_da_chet', topic: '{TOPIC}'}})
WHERE cc IN ['bi_tuyen_bo_da_chet', 'tong_quat', 'khong_ro']
OPTIONAL MATCH (dk_tb:DieuKien:{TOPIC_LABEL} {{id: 'mot_ben_bi_toa_an_tuyen_bo_da_chet', topic: '{TOPIC}'}})
WHERE qt_tb IS NOT NULL
OPTIONAL MATCH (hq_tb:HauQua:{TOPIC_LABEL} {{id: 'hon_nhan_cham_dut_theo_ngay_chet_ghi_trong_ban_an_quyet_dinh', topic: '{TOPIC}'}})
WHERE qt_tb IS NOT NULL
OPTIONAL MATCH (tthn_tb:TinhTrangHonNhan:{TOPIC_LABEL} {{id: 'hon_nhan_cham_dut_do_mot_ben_chet_hoac_bi_tuyen_bo_da_chet', topic: '{TOPIC}'}})
WHERE hq_tb IS NOT NULL

OPTIONAL MATCH (dk_bt:DieuKien:{TOPIC_LABEL} {{id: 'chi_biet_tich_chua_co_tuyen_bo_da_chet', topic: '{TOPIC}'}})
WHERE cc = 'biet_tich_chua_co_tuyen_bo'
OPTIONAL MATCH (tthn_bt:TinhTrangHonNhan:{TOPIC_LABEL} {{id: 'biet_tich_chua_tu_lam_cham_dut_hon_nhan', topic: '{TOPIC}'}})
WHERE dk_bt IS NOT NULL

WITH wl, cc, kc,
  [x IN collect(DISTINCT dk_ct) + collect(DISTINCT hq_ct) + collect(DISTINCT tthn_ct)
       + collect(DISTINCT qt_tb) + collect(DISTINCT dk_tb) + collect(DISTINCT hq_tb)
       + collect(DISTINCT tthn_tb) + collect(DISTINCT dk_bt) + collect(DISTINCT tthn_bt)
   WHERE x IS NOT NULL] AS seed_nodes,
  CASE cc
    WHEN 'chet_thuc_te' THEN
      [x IN collect(DISTINCT dk_ct) + collect(DISTINCT hq_ct) + collect(DISTINCT tthn_ct)
       WHERE x IS NOT NULL]
    WHEN 'bi_tuyen_bo_da_chet' THEN
      [x IN collect(DISTINCT qt_tb) + collect(DISTINCT dk_tb) + collect(DISTINCT hq_tb)
           + collect(DISTINCT tthn_tb)
       WHERE x IS NOT NULL]
    WHEN 'biet_tich_chua_co_tuyen_bo' THEN
      [x IN collect(DISTINCT dk_bt) + collect(DISTINCT tthn_bt) WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT hq_ct) + collect(DISTINCT hq_tb) + collect(DISTINCT tthn_ct)
       WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: ThoiDiemChamDutHonNhanDoChetParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "cc": params.can_cu_cham_dut,
        "kc": params.khia_canh_thoi_diem,
        "whitelist_dieu_ids": _DIEU_65_WHITELIST if use_wl else [],
    }


thoi_diem_cham_dut_hon_nhan_do_chet = CypherTemplate(
    name="thoi_diem_cham_dut_hon_nhan_do_chet",
    description=(
        "Xác định hôn nhân có chấm dứt hay không và thời điểm chấm dứt khi một bên "
        "chết thực tế hoặc bị Tòa án tuyên bố là đã chết theo Điều 65. "
        "Không đồng nhất biệt tích với chết hoặc tuyên bố đã chết. "
        "Ví dụ: Chồng chết thì quan hệ hôn nhân có chấm dứt không?; "
        "Người chồng biệt tích bao nhiêu năm thì người vợ có thể kết hôn với chồng mới?; "
        "Thời điểm chấm dứt hôn nhân là khi nào?"
    ),
    params_schema=ThoiDiemChamDutHonNhanDoChetParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
