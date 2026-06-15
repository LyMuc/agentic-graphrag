"""Template — trách nhiệm liên đới của vợ chồng (Đ27 + căn cứ bổ trợ)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.dai_dien_trach_nhiem_vo_chong._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("nhom_can_cu",)
_DIEU_27_WHITELIST = ["Luat_HNGD_2014_Dieu_27"]

_MUC_DICH_TO_DIEU_KIEN: dict[str, str] = {
    "nhu_cau_gia_dinh": "no_phuc_vu_nhu_cau_gia_dinh",
    "kinh_doanh_chung": "no_phuc_vu_kinh_doanh_chung",
    "ca_nhan": "no_phuc_vu_muc_dich_ca_nhan",
}


class TrachNhiemLienDoiVoChongParams(BaseModel):
    nhom_can_cu: Literal[
        "giao_dich_dai_dien",
        "nghia_vu_chung",
        "doi_chieu_chung_rieng",
        "ly_hon_nguoi_thu_ba",
        "tong_quat",
    ] = Field(default="tong_quat")
    muc_dich_no: Literal[
        "nhu_cau_gia_dinh", "kinh_doanh_chung", "ca_nhan", "khong_ro"
    ] = Field(default="khong_ro")
    thoi_diem_no: Literal[
        "truoc_hon_nhan", "trong_hon_nhan", "sau_ly_hon", "khong_ro"
    ] = Field(default="khong_ro")
    tinh_trang_hon_nhan: Literal[
        "dang_hon_nhan", "dang_ly_hon", "da_ly_hon", "khong_ro"
    ] = Field(default="khong_ro")
    nguoi_thu_ba: Literal["ngan_hang", "chu_no", "nguoi_thu_ba", "khong_ro"] = Field(
        default="khong_ro"
    )
    tai_san_thanh_toan: Literal["tai_san_chung", "tai_san_rieng", "khong_ro"] = Field(
        default="khong_ro"
    )


_SEED_BODY = f"""
WITH $nhom_can_cu AS ncc, $muc_dich_no AS mdn, $tai_san_thanh_toan AS tst,
     $whitelist_dieu_ids AS wl

OPTIONAL MATCH (nv_ld1:NghiaVu:{TOPIC_LABEL} {{
  id: 'nghia_vu_lien_doi_tu_giao_dich_mot_ben', topic: '{TOPIC}'
}})
OPTIONAL MATCH (nv_ld2:NghiaVu:{TOPIC_LABEL} {{
  id: 'nghia_vu_lien_doi_tu_giao_dich_phu_hop_dai_dien', topic: '{TOPIC}'
}})
OPTIONAL MATCH (nv_ld3:NghiaVu:{TOPIC_LABEL} {{
  id: 'nghia_vu_lien_doi_tu_nghia_vu_chung', topic: '{TOPIC}'
}})
OPTIONAL MATCH (nv_chung:NghiaVu:{TOPIC_LABEL} {{
  id: 'nghia_vu_chung_cua_vo_chong', topic: '{TOPIC}'
}})
OPTIONAL MATCH (nv_rieng:NghiaVu:{TOPIC_LABEL} {{
  id: 'nghia_vu_rieng_cua_mot_ben', topic: '{TOPIC}'
}})
OPTIONAL MATCH (gd_nhu_cau:GiaoDich:{TOPIC_LABEL} {{
  id: 'giao_dich_mot_ben_dap_ung_nhu_cau_thiet_yeu', topic: '{TOPIC}'
}})
OPTIONAL MATCH (hv_tt:HanhVi:{TOPIC_LABEL} {{
  id: 'thanh_toan_no_bang_tai_san_chung', topic: '{TOPIC}'
}})
OPTIONAL MATCH (hv_ly:HanhVi:{TOPIC_LABEL} {{
  id: 'giai_quyet_no_khi_ly_hon', topic: '{TOPIC}'
}})
OPTIONAL MATCH (nv_ly:NghiaVu:{TOPIC_LABEL} {{
  id: 'trach_nhiem_voi_nguoi_thu_ba_khi_ly_hon', topic: '{TOPIC}'
}})
OPTIONAL MATCH (dk_tk:DieuKien:{TOPIC_LABEL} {{
  id: 'no_phat_sinh_trong_thoi_ky_hon_nhan', topic: '{TOPIC}'
}})
OPTIONAL MATCH (dk_md:DieuKien:{TOPIC_LABEL} {{id: $dk_muc_dich_id, topic: '{TOPIC}'}})
WHERE $dk_muc_dich_id <> ''

WITH wl, ncc, mdn, tst,
  collect(DISTINCT nv_ld1) AS c_ld1,
  collect(DISTINCT nv_ld2) AS c_ld2,
  collect(DISTINCT nv_ld3) AS c_ld3,
  collect(DISTINCT nv_chung) AS c_chung,
  collect(DISTINCT nv_rieng) AS c_rieng,
  collect(DISTINCT gd_nhu_cau) AS c_gd_nc,
  collect(DISTINCT hv_tt) AS c_hv_tt,
  collect(DISTINCT hv_ly) AS c_hv_ly,
  collect(DISTINCT nv_ly) AS c_nv_ly,
  collect(DISTINCT dk_tk) AS c_dk_tk,
  collect(DISTINCT dk_md) AS c_dk_md

WITH wl, ncc, mdn, tst,
  [x IN c_ld1 + c_ld2 + c_ld3 + c_chung + c_rieng + c_gd_nc + c_hv_tt + c_hv_ly
      + c_nv_ly + c_dk_tk + c_dk_md
   WHERE x IS NOT NULL] AS seed_nodes,
  CASE ncc
    WHEN 'giao_dich_dai_dien' THEN
      [x IN c_ld1 + c_ld2 + (CASE WHEN mdn = 'nhu_cau_gia_dinh' THEN c_gd_nc ELSE [] END)
       WHERE x IS NOT NULL]
    WHEN 'nghia_vu_chung' THEN
      [x IN c_ld3 + c_chung + c_dk_tk + c_dk_md WHERE x IS NOT NULL]
    WHEN 'doi_chieu_chung_rieng' THEN
      [x IN c_chung + c_rieng + c_dk_md
          + (CASE WHEN tst = 'tai_san_chung' THEN c_hv_tt ELSE [] END)
       WHERE x IS NOT NULL]
    WHEN 'ly_hon_nguoi_thu_ba' THEN
      [x IN c_hv_ly + c_nv_ly + c_dk_tk + c_dk_md WHERE x IS NOT NULL]
    ELSE
      [x IN c_ld1 + c_ld2 + c_ld3 + c_chung + c_rieng WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: TrachNhiemLienDoiVoChongParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    dk_muc_dich_id = _MUC_DICH_TO_DIEU_KIEN.get(params.muc_dich_no, "")
    return {
        "whitelist_dieu_ids": _DIEU_27_WHITELIST if use_wl else [],
        "dk_muc_dich_id": dk_muc_dich_id,
        **params.model_dump(),
    }


trach_nhiem_lien_doi_vo_chong = CypherTemplate(
    name="trach_nhiem_lien_doi_vo_chong",
    description=(
        "Trách nhiệm liên đới từ giao dịch một bên, nghĩa vụ chung/riêng, đối chiếu "
        "nợ chung-riêng và nghĩa vụ với người thứ ba khi ly hôn (Đ27 k1-k2, tham chiếu "
        "Đ30/37/45/60). Phù hợp khi có 'nợ', 'vay', 'trả nợ', 'trách nhiệm liên đới', "
        "'ngân hàng', 'chủ nợ', 'sau ly hôn'."
    ),
    params_schema=TrachNhiemLienDoiVoChongParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
