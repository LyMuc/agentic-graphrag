"""Template — người có quyền yêu cầu xác định cha, mẹ, con (Đ102)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.xac_dinh_cha_me_con._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
)

_DIEU_WHITELIST = ["Luat_HNGD_2014_Dieu_102"]


class NguoiCoQuyenYeuCauXacDinhChaMeConParams(BaseModel):
    kenh_yeu_cau: Literal["ho_tich", "toa_an", "khong_ro"] = Field(default="khong_ro")
    nhom_nguoi_yeu_cau: Literal[
        "cha",
        "me",
        "con",
        "cha_me_con",
        "nguoi_giam_ho",
        "co_quan_gia_dinh",
        "co_quan_tre_em",
        "hoi_lien_hiep_phu_nu",
        "tong_hop",
    ] = Field(default="tong_hop")
    doi_tuong_duoc_bao_ve: Literal[
        "ban_than",
        "con_chua_thanh_nien",
        "con_thanh_nien_mat_nang_luc_hanh_vi_dan_su",
        "cha_me_chua_thanh_nien",
        "cha_me_mat_nang_luc_hanh_vi_dan_su",
        "khong_ro",
    ] = Field(default="khong_ro")
    tinh_trang_tranh_chap: Literal["khong_co", "co", "khong_ro"] = Field(default="khong_ro")


_SEED_BODY = f"""
WITH $kenh_yeu_cau AS ky, $nhom_nguoi_yeu_cau AS nn, $doi_tuong_duoc_bao_ve AS dtb,
     $whitelist_dieu_ids AS wl

OPTIONAL MATCH (ct_ht:ChuThe:{TOPIC_LABEL} {{
  id: 'cha_me_con_thanh_nien_khong_mat_nang_luc_hanh_vi', topic: '{TOPIC}'
}})
WHERE ky = 'ho_tich' OR (nn IN ['cha_me_con', 'cha', 'me', 'con'] AND dtb = 'ban_than')

OPTIONAL MATCH (q_ht:Quyen:{TOPIC_LABEL} {{
  id: 'yeu_cau_ho_tich_xac_dinh_cho_minh', topic: '{TOPIC}'
}})
WHERE ky = 'ho_tich' OR (nn IN ['cha_me_con', 'cha', 'me', 'con'] AND dtb = 'ban_than')

OPTIONAL MATCH (q_ta:Quyen:{TOPIC_LABEL} {{
  id: 'cha_me_con_yeu_cau_toa_an_xac_dinh_cho_minh', topic: '{TOPIC}'
}})
WHERE ky = 'toa_an' AND nn IN ['cha_me_con', 'cha', 'me', 'con'] AND dtb = 'ban_than'

OPTIONAL MATCH (ct_gh:ChuThe:{TOPIC_LABEL} {{
  id: 'cha_me_con_hoac_nguoi_giam_ho', topic: '{TOPIC}'
}})
WHERE nn = 'nguoi_giam_ho' OR nn = 'tong_hop'

OPTIONAL MATCH (cq_gd:CoQuan:{TOPIC_LABEL} {{
  id: 'co_quan_quan_ly_nha_nuoc_ve_gia_dinh', topic: '{TOPIC}'
}})
WHERE nn = 'co_quan_gia_dinh' OR nn = 'tong_hop'

OPTIONAL MATCH (cq_te:CoQuan:{TOPIC_LABEL} {{
  id: 'co_quan_quan_ly_nha_nuoc_ve_tre_em', topic: '{TOPIC}'
}})
WHERE nn = 'co_quan_tre_em' OR nn = 'tong_hop'

OPTIONAL MATCH (cq_pn:CoQuan:{TOPIC_LABEL} {{
  id: 'hoi_lien_hiep_phu_nu', topic: '{TOPIC}'
}})
WHERE nn = 'hoi_lien_hiep_phu_nu' OR nn = 'tong_hop'

OPTIONAL MATCH (q_bv:Quyen:{TOPIC_LABEL} {{
  id: 'yeu_cau_toa_an_xac_dinh_cho_nguoi_duoc_bao_ve', topic: '{TOPIC}'
}})
WHERE nn IN ['nguoi_giam_ho', 'co_quan_gia_dinh', 'co_quan_tre_em', 'hoi_lien_hiep_phu_nu', 'tong_hop']

OPTIONAL MATCH (ct_con_bv:ChuThe:{TOPIC_LABEL} {{
  id: 'con_chua_thanh_nien_hoac_thanh_nien_mat_nang_luc', topic: '{TOPIC}'
}})
WHERE dtb IN ['con_chua_thanh_nien', 'con_thanh_nien_mat_nang_luc_hanh_vi_dan_su', 'khong_ro']
  AND nn IN ['nguoi_giam_ho', 'co_quan_gia_dinh', 'co_quan_tre_em', 'hoi_lien_hiep_phu_nu', 'tong_hop']

OPTIONAL MATCH (ct_cm_bv:ChuThe:{TOPIC_LABEL} {{
  id: 'cha_me_chua_thanh_nien_hoac_mat_nang_luc', topic: '{TOPIC}'
}})
WHERE dtb IN ['cha_me_chua_thanh_nien', 'cha_me_mat_nang_luc_hanh_vi_dan_su']

WITH wl, ky, nn, dtb,
  ct_ht, q_ht, q_ta, ct_gh, cq_gd, cq_te, cq_pn, q_bv, ct_con_bv, ct_cm_bv,
  [x IN collect(DISTINCT ct_ht) + collect(DISTINCT q_ht) + collect(DISTINCT q_ta)
       + collect(DISTINCT ct_gh) + collect(DISTINCT cq_gd) + collect(DISTINCT cq_te)
       + collect(DISTINCT cq_pn) + collect(DISTINCT q_bv)
       + collect(DISTINCT ct_con_bv) + collect(DISTINCT ct_cm_bv)
   WHERE x IS NOT NULL] AS seed_nodes,
  CASE
    WHEN ky = 'ho_tich' THEN [x IN [ct_ht, q_ht] WHERE x IS NOT NULL]
    WHEN ky = 'toa_an' AND nn IN ['cha_me_con', 'cha', 'me', 'con'] THEN [x IN [q_ta] WHERE x IS NOT NULL]
    WHEN nn = 'nguoi_giam_ho' THEN
      [x IN [ct_gh, q_bv, ct_con_bv, ct_cm_bv] WHERE x IS NOT NULL]
    WHEN nn = 'co_quan_gia_dinh' THEN
      [x IN [cq_gd, q_bv, ct_con_bv] WHERE x IS NOT NULL]
    WHEN nn = 'co_quan_tre_em' THEN
      [x IN [cq_te, q_bv, ct_con_bv] WHERE x IS NOT NULL]
    WHEN nn = 'hoi_lien_hiep_phu_nu' THEN
      [x IN [cq_pn, q_bv, ct_con_bv] WHERE x IS NOT NULL]
    WHEN nn = 'tong_hop' THEN
      [x IN [ct_gh, cq_gd, cq_te, cq_pn, q_bv, ct_con_bv, ct_cm_bv] WHERE x IS NOT NULL]
    ELSE []
  END AS leaf_seed_nodes
"""


def _params_builder(params: NguoiCoQuyenYeuCauXacDinhChaMeConParams) -> dict[str, Any]:
    use_wl = params.kenh_yeu_cau == "khong_ro" and params.nhom_nguoi_yeu_cau == "tong_hop"
    return {
        "kenh_yeu_cau": params.kenh_yeu_cau,
        "nhom_nguoi_yeu_cau": params.nhom_nguoi_yeu_cau,
        "doi_tuong_duoc_bao_ve": params.doi_tuong_duoc_bao_ve,
        "whitelist_dieu_ids": _DIEU_WHITELIST if use_wl else [],
    }


nguoi_co_quyen_yeu_cau_xac_dinh_cha_me_con = CypherTemplate(
    name="nguoi_co_quyen_yeu_cau_xac_dinh_cha_me_con",
    description=(
        "Ai có quyền yêu cầu cơ quan hộ tịch hoặc Tòa án xác định cha, mẹ, con (Đ102): "
        "cha/mẹ/con thành niên; người giám hộ; cơ quan quản lý gia đình/trẻ em; "
        "Hội Liên hiệp Phụ nữ cho người chưa thành niên hoặc mất năng lực. "
        "Ví dụ: 'người giám hộ có quyền yêu cầu không'; 'Hội Liên hiệp Phụ nữ'."
    ),
    params_schema=NguoiCoQuyenYeuCauXacDinhChaMeConParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
