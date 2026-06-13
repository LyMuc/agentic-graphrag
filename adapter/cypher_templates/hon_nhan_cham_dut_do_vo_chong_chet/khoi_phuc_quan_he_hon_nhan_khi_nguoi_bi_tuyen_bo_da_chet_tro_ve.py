"""Template — khôi phục quan hệ hôn nhân khi người bị tuyên bố đã chết trở về (Đ67 k1)."""
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

_ROUTER_FIELDS = ("khia_canh_khoi_phuc", "loai_quyet_dinh_truoc_khi_tro_ve")
_DIEU_67_K1_WHITELIST = ["Luat_HNGD_2014_Dieu_67_Khoan_1"]


class KhoiPhucQuanHeHonNhanParams(BaseModel):
    loai_quyet_dinh_truoc_khi_tro_ve: Literal[
        "tuyen_bo_da_chet",
        "tuyen_bo_mat_tich",
        "khong_ro",
    ] = Field(
        description=(
            "Giữ nguyên dữ kiện người dùng; tuyệt đối không normalize "
            "tuyen_bo_mat_tich thành tuyen_bo_da_chet."
        )
    )
    tinh_trang_cua_ben_con_lai: Literal[
        "chua_ket_hon_nguoi_khac",
        "da_co_quyet_dinh_ly_hon",
        "da_ket_hon_nguoi_khac",
        "khong_ro",
    ] = Field(description="Chọn nhánh Điều 67 khoản 1.")
    quyet_dinh_huy_bo_tuyen_bo_da_chet: Literal["da_co", "chua_co", "khong_ro"] = Field(
        description="Tòa hủy bỏ tuyên bố đã chết → da_co; chỉ nói trở về → khong_ro."
    )
    khia_canh_khoi_phuc: Literal[
        "dieu_kien_khoi_phuc",
        "hieu_luc_quyet_dinh_ly_hon",
        "hieu_luc_hon_nhan_sau",
        "co_duoc_khoi_phuc_hay_khong",
        "tong_quat",
    ] = Field(description="Trọng tâm câu hỏi về khôi phục hôn nhân.")


_SEED_BODY = f"""
WITH $loai AS loai, $tt AS tt, $huy AS huy, $kc AS kc, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (ct_tv:ChuThe:{TOPIC_LABEL} {{id: 'nguoi_bi_tuyen_bo_da_chet_tro_ve', topic: '{TOPIC}'}})
WHERE loai IN ['tuyen_bo_da_chet', 'khong_ro']
OPTIONAL MATCH (qt_huy:QuyTrinhPhapLy:{TOPIC_LABEL} {{id: 'toa_an_huy_bo_tuyen_bo_vo_hoac_chong_da_chet', topic: '{TOPIC}'}})
WHERE loai IN ['tuyen_bo_da_chet', 'khong_ro']

OPTIONAL MATCH (dk_xm:DieuKien:{TOPIC_LABEL} {{id: 'can_xac_minh_quyet_dinh_mat_tich_hay_tuyen_bo_da_chet', topic: '{TOPIC}'}})
WHERE loai = 'tuyen_bo_mat_tich'

OPTIONAL MATCH (dk_ck:DieuKien:{TOPIC_LABEL} {{id: 'ben_con_lai_chua_ket_hon_voi_nguoi_khac', topic: '{TOPIC}'}})
WHERE tt IN ['chua_ket_hon_nguoi_khac', 'tong_quat', 'khong_ro'] OR kc IN ['dieu_kien_khoi_phuc', 'co_duoc_khoi_phuc_hay_khong', 'tong_quat']
OPTIONAL MATCH (hq_kp:HauQua:{TOPIC_LABEL} {{id: 'quan_he_hon_nhan_duoc_khoi_phuc', topic: '{TOPIC}'}})
WHERE dk_ck IS NOT NULL
OPTIONAL MATCH (tthn_kp:TinhTrangHonNhan:{TOPIC_LABEL} {{id: 'hon_nhan_duoc_khoi_phuc_tu_thoi_diem_ket_hon', topic: '{TOPIC}'}})
WHERE hq_kp IS NOT NULL

OPTIONAL MATCH (qt_lh:QuyTrinhPhapLy:{TOPIC_LABEL} {{id: 'quyet_dinh_cho_ly_hon_voi_nguoi_bi_tuyen_bo_mat_tich', topic: '{TOPIC}'}})
WHERE tt IN ['da_co_quyet_dinh_ly_hon', 'tong_quat', 'khong_ro'] OR kc = 'hieu_luc_quyet_dinh_ly_hon'
OPTIONAL MATCH (dk_lh:DieuKien:{TOPIC_LABEL} {{id: 'da_co_quyet_dinh_cho_ly_hon', topic: '{TOPIC}'}})
WHERE qt_lh IS NOT NULL
OPTIONAL MATCH (hq_lh:HauQua:{TOPIC_LABEL} {{id: 'quyet_dinh_cho_ly_hon_van_co_hieu_luc', topic: '{TOPIC}'}})
WHERE dk_lh IS NOT NULL

OPTIONAL MATCH (dk_kh:DieuKien:{TOPIC_LABEL} {{id: 'ben_con_lai_da_ket_hon_voi_nguoi_khac', topic: '{TOPIC}'}})
WHERE tt IN ['da_ket_hon_nguoi_khac', 'tong_quat', 'khong_ro'] OR kc = 'hieu_luc_hon_nhan_sau'
OPTIONAL MATCH (hq_sau:HauQua:{TOPIC_LABEL} {{id: 'quan_he_hon_nhan_xac_lap_sau_co_hieu_luc', topic: '{TOPIC}'}})
WHERE dk_kh IS NOT NULL
OPTIONAL MATCH (tthn_sau:TinhTrangHonNhan:{TOPIC_LABEL} {{id: 'hon_nhan_xac_lap_sau_co_hieu_luc', topic: '{TOPIC}'}})
WHERE hq_sau IS NOT NULL

WITH wl, loai, tt, kc,
  [x IN collect(DISTINCT ct_tv) + collect(DISTINCT qt_huy) + collect(DISTINCT dk_xm)
       + collect(DISTINCT dk_ck) + collect(DISTINCT hq_kp) + collect(DISTINCT tthn_kp)
       + collect(DISTINCT qt_lh) + collect(DISTINCT dk_lh) + collect(DISTINCT hq_lh)
       + collect(DISTINCT dk_kh) + collect(DISTINCT hq_sau) + collect(DISTINCT tthn_sau)
   WHERE x IS NOT NULL] AS seed_nodes,
  CASE
    WHEN loai = 'tuyen_bo_mat_tich' THEN
      [x IN collect(DISTINCT dk_xm) WHERE x IS NOT NULL]
    WHEN tt = 'chua_ket_hon_nguoi_khac' THEN
      [x IN collect(DISTINCT dk_ck) + collect(DISTINCT hq_kp) + collect(DISTINCT tthn_kp)
       WHERE x IS NOT NULL]
    WHEN tt = 'da_co_quyet_dinh_ly_hon' THEN
      [x IN collect(DISTINCT qt_lh) + collect(DISTINCT hq_lh) WHERE x IS NOT NULL]
    WHEN tt = 'da_ket_hon_nguoi_khac' THEN
      [x IN collect(DISTINCT dk_kh) + collect(DISTINCT hq_sau) + collect(DISTINCT tthn_sau)
       WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT hq_kp) + collect(DISTINCT hq_lh) + collect(DISTINCT hq_sau)
       WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: KhoiPhucQuanHeHonNhanParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    wl = _DIEU_67_K1_WHITELIST if use_wl or params.loai_quyet_dinh_truoc_khi_tro_ve == "tuyen_bo_mat_tich" else []
    return {
        "loai": params.loai_quyet_dinh_truoc_khi_tro_ve,
        "tt": params.tinh_trang_cua_ben_con_lai,
        "huy": params.quyet_dinh_huy_bo_tuyen_bo_da_chet,
        "kc": params.khia_canh_khoi_phuc,
        "whitelist_dieu_ids": wl,
    }


khoi_phuc_quan_he_hon_nhan_khi_nguoi_bi_tuyen_bo_da_chet_tro_ve = CypherTemplate(
    name="khoi_phuc_quan_he_hon_nhan_khi_nguoi_bi_tuyen_bo_da_chet_tro_ve",
    description=(
        "Xác định quan hệ hôn nhân cũ có được khôi phục khi Tòa án hủy bỏ quyết định "
        "tuyên bố một người là đã chết; xử lý nhánh đã có quyết định ly hôn hoặc "
        "bên còn lại đã kết hôn với người khác. Không coi tuyên bố mất tích đồng nghĩa "
        "tuyên bố đã chết. "
        "Ví dụ: Người bị tòa án tuyên bố đã chết mà trở về thì quan hệ hôn nhân trước đó "
        "có còn được pháp luật thừa nhận?; "
        "Người bị tuyên bố mất tích trở về sau khi chồng kết hôn người khác có được "
        "khôi phục hôn nhân hay không?"
    ),
    params_schema=KhoiPhucQuanHeHonNhanParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
