"""Template — phương thức và tạm ngừng cấp dưỡng (Đ117)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.cap_duong._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("khia_canh",)
_DIEU_117_WHITELIST = ["Luat_HNGD_2014_Dieu_117"]

_CHU_KY_TO_PT = {
    "hang_thang": "cap_duong_hang_thang",
    "hang_quy": "cap_duong_hang_quy",
    "nua_nam": "cap_duong_nua_nam",
    "hang_nam": "cap_duong_hang_nam",
    "mot_lan": "cap_duong_mot_lan",
}


class PhuongThucVaTamNgungCapDuongParams(BaseModel):
    khia_canh: Literal[
        "cac_phuong_thuc",
        "thay_doi_phuong_thuc",
        "tam_ngung_do_kho_khan",
        "tong_quat",
    ] = Field(
        description=(
            "Khía cạnh phương thức. Map: có mấy cách/phương thức nào → cac_phuong_thuc; "
            "đổi cách/đổi kỳ trả → thay_doi_phuong_thuc; tạm dừng/tạm ngừng "
            "→ tam_ngung_do_kho_khan."
        )
    )
    chu_ky: Literal[
        "hang_thang",
        "hang_quy",
        "nua_nam",
        "hang_nam",
        "mot_lan",
        "tat_ca",
        "khong_ro",
    ] = Field(description="Chu kỳ cấp dưỡng (hàng tháng, hàng quý, một lần...).")
    doi_tuong_nhan: Literal["con", "vo_chong_cu", "khac", "khong_ro"] = Field(
        description="Đối tượng được cấp dưỡng."
    )
    kho_khan_kinh_te: Literal["co", "khong", "khong_ro"] = Field(
        description="Người có nghĩa vụ gặp khó khăn kinh tế."
    )
    so_luong_ben: Literal[
        "mot_voi_mot",
        "mot_nguoi_cap_duong_nhieu_nguoi",
        "nhieu_nguoi_cung_cap_duong",
        "khong_ro",
    ] = Field(description="Số lượng bên (để bổ sung Đ108/109 nếu cần).")


_SEED_BODY = f"""
WITH $khia_canh AS kc, $chu_ky AS ck, $pt_id AS pt_id, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (pt:PhuongThucCapDuong:{TOPIC_LABEL})
WHERE pt.topic = '{TOPIC}'
  AND kc IN ['cac_phuong_thuc', 'tong_quat']
  AND (ck = 'tat_ca' OR ck = 'khong_ro' OR pt.id = pt_id)

OPTIONAL MATCH (tt_td:ThoaThuan:{TOPIC_LABEL} {{id: 'thoa_thuan_thay_doi_phuong_thuc_cap_duong', topic: '{TOPIC}'}})
WHERE kc = 'thay_doi_phuong_thuc'

OPTIONAL MATCH (hv_tn:HanhVi:{TOPIC_LABEL} {{id: 'tam_ngung_cap_duong', topic: '{TOPIC}'}})
WHERE kc = 'tam_ngung_do_kho_khan'
OPTIONAL MATCH (tt_tn:ThoaThuan:{TOPIC_LABEL} {{id: 'thoa_thuan_tam_ngung_cap_duong', topic: '{TOPIC}'}})
WHERE hv_tn IS NOT NULL
OPTIONAL MATCH (dk_tn:DieuKien:{TOPIC_LABEL} {{
  id: 'kho_khan_kinh_te_khong_co_kha_nang_thuc_hien', topic: '{TOPIC}'
}})
WHERE hv_tn IS NOT NULL

OPTIONAL MATCH (qh:QuanHeCapDuong:{TOPIC_LABEL} {{id: 'vo_chong_sau_ly_hon', topic: '{TOPIC}'}})
WHERE $doi_tuong_nhan = 'vo_chong_cu'

WITH wl, kc,
  [x IN collect(DISTINCT pt) + collect(DISTINCT tt_td)
       + collect(DISTINCT hv_tn) + collect(DISTINCT tt_tn) + collect(DISTINCT dk_tn)
       + collect(DISTINCT qh)
   WHERE x IS NOT NULL] AS seed_nodes,
  CASE kc
    WHEN 'thay_doi_phuong_thuc' THEN
      [x IN collect(DISTINCT tt_td) WHERE x IS NOT NULL]
    WHEN 'tam_ngung_do_kho_khan' THEN
      [x IN collect(DISTINCT hv_tn) + collect(DISTINCT tt_tn) + collect(DISTINCT dk_tn)
       WHERE x IS NOT NULL]
    WHEN 'cac_phuong_thuc' THEN
      [x IN collect(DISTINCT pt) WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT pt) + collect(DISTINCT qh) WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: PhuongThucVaTamNgungCapDuongParams) -> dict[str, Any]:
    pt_id = _CHU_KY_TO_PT.get(params.chu_ky, "")
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "khia_canh": params.khia_canh,
        "chu_ky": params.chu_ky,
        "pt_id": pt_id,
        "doi_tuong_nhan": params.doi_tuong_nhan,
        "whitelist_dieu_ids": _DIEU_117_WHITELIST if use_wl else [],
    }


phuong_thuc_va_tam_ngung_cap_duong = CypherTemplate(
    name="phuong_thuc_va_tam_ngung_cap_duong",
    description=(
        "Các phương thức cấp dưỡng theo chu kỳ, thay đổi phương thức và tạm ngừng khi "
        "người có nghĩa vụ khó khăn kinh tế (Đ117). "
        "Ví dụ: phương thức cấp dưỡng nuôi con hiện nay có mấy cách; "
        "khó khăn kinh tế xin tạm ngừng nghĩa vụ; "
        "phương thức cấp dưỡng giữa vợ chồng sau ly hôn."
    ),
    params_schema=PhuongThucVaTamNgungCapDuongParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
