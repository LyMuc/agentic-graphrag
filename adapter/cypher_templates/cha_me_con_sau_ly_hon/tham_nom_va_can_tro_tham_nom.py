"""Template — thăm nom và cản trở thăm nom (Đ82 K3, Đ83 K2)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.cha_me_con_sau_ly_hon._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("khia_canh_tham_nom",)
_TONG_QUAT_WHITELIST = [
    "Luat_HNGD_2014_Dieu_82_Khoan_3",
    "Luat_HNGD_2014_Dieu_83_Khoan_2",
]


class ThamNomVaCanTroThamNomParams(BaseModel):
    khia_canh_tham_nom: Literal[
        "quyen_tham_nom",
        "can_tro_tham_nom",
        "lam_dung_tham_nom",
        "yeu_cau_han_che_tham_nom",
        "xu_ly_hanh_vi_can_tro",
        "tong_quat",
    ] = Field(
        description=(
            "Khía cạnh thăm nom. Map: được gặp/thăm con → quyen_tham_nom; "
            "ngăn/cấm/cản → can_tro_tham_nom; lạm dụng thăm nom → lam_dung_tham_nom; "
            "xin hạn chế → yeu_cau_han_che_tham_nom; bị phạt/xử lý → xu_ly_hanh_vi_can_tro."
        )
    )
    chu_the_co_hanh_vi: Literal[
        "nguoi_truc_tiep_nuoi",
        "nguoi_khong_truc_tiep_nuoi",
        "thanh_vien_gia_dinh",
        "khong_ro",
    ] = Field(description="Chủ thể có hành vi cản trở hoặc lạm dụng thăm nom.")
    tinh_trang_cap_duong: Literal[
        "co_thuc_hien",
        "khong_thuc_hien",
        "dang_tranh_chap",
        "khong_ro",
    ] = Field(
        description=(
            "Tình trạng cấp dưỡng (fact phụ). Không cấp dưỡng không tự loại bỏ quyền thăm nom."
        )
    )
    anh_huong_xau_den_con: Literal["co", "khong", "khong_ro"] = Field(
        description="Có gây ảnh hưởng xấu/cản trợ chăm sóc/đe dọa con → co."
    )


_SEED_BODY = f"""
WITH $khia_canh_tham_nom AS kc, $chu_the_co_hanh_vi AS ct_hv, $anh_huong_xau_den_con AS ah,
     $whitelist_dieu_ids AS wl

OPTIONAL MATCH (q:Quyen:{TOPIC_LABEL} {{id: 'quyen_tham_nom_con_khong_bi_can_tro', topic: '{TOPIC}'}})
WHERE kc IN ['quyen_tham_nom', 'tong_quat']
OPTIONAL MATCH (nv3:NghiaVu:{TOPIC_LABEL} {{id: 'nghia_vu_tham_nom_con', topic: '{TOPIC}'}})
WHERE kc IN ['quyen_tham_nom', 'tong_quat']
OPTIONAL MATCH (hv3:HanhVi:{TOPIC_LABEL} {{id: 'tham_nom_con_sau_ly_hon', topic: '{TOPIC}'}})
WHERE kc IN ['quyen_tham_nom', 'tong_quat']

OPTIONAL MATCH (hv_ct:HanhVi:{TOPIC_LABEL} {{id: 'can_tro_viec_tham_nom_con', topic: '{TOPIC}'}})
WHERE kc IN ['can_tro_tham_nom', 'xu_ly_hanh_vi_can_tro', 'tong_quat']
OPTIONAL MATCH (nv83:NghiaVu:{TOPIC_LABEL} {{
  id: 'nghia_vu_khong_can_tro_tham_nom_cham_soc_con', topic: '{TOPIC}'
}})
WHERE kc IN ['can_tro_tham_nom', 'xu_ly_hanh_vi_can_tro', 'tong_quat']
  AND ct_hv IN ['nguoi_truc_tiep_nuoi', 'thanh_vien_gia_dinh', 'khong_ro']

OPTIONAL MATCH (hv_ld:HanhVi:{TOPIC_LABEL} {{id: 'lam_dung_viec_tham_nom_con', topic: '{TOPIC}'}})
WHERE kc IN ['lam_dung_tham_nom', 'yeu_cau_han_che_tham_nom', 'tong_quat']
OPTIONAL MATCH (hv_ld)-[:AP_DUNG_KHI]->(dk_ld:DieuKien:{TOPIC_LABEL})
WHERE kc IN ['lam_dung_tham_nom', 'yeu_cau_han_che_tham_nom', 'tong_quat']
  AND (ah = 'co' OR kc = 'lam_dung_tham_nom')

OPTIONAL MATCH (qy:Quyen:{TOPIC_LABEL} {{id: 'quyen_yeu_cau_toa_an_han_che_tham_nom', topic: '{TOPIC}'}})
WHERE kc IN ['lam_dung_tham_nom', 'yeu_cau_han_che_tham_nom', 'tong_quat']
OPTIONAL MATCH (qy)-[:THUC_HIEN]->(hv_yc:HanhVi:{TOPIC_LABEL} {{
  id: 'yeu_cau_toa_an_han_che_quyen_tham_nom', topic: '{TOPIC}'
}})
WHERE kc IN ['lam_dung_tham_nom', 'yeu_cau_han_che_tham_nom', 'tong_quat']
OPTIONAL MATCH (hv_yc)-[:DAN_TOI]->(hq:HauQua:{TOPIC_LABEL} {{
  id: 'toa_an_han_che_quyen_tham_nom', topic: '{TOPIC}'
}})
WHERE kc IN ['lam_dung_tham_nom', 'yeu_cau_han_che_tham_nom', 'tong_quat']

WITH wl, kc,
  collect(DISTINCT q) + collect(DISTINCT nv3) + collect(DISTINCT hv3)
    + collect(DISTINCT hv_ct) + collect(DISTINCT nv83)
    + collect(DISTINCT hv_ld) + collect(DISTINCT dk_ld)
    + collect(DISTINCT qy) + collect(DISTINCT hv_yc) + collect(DISTINCT hq) AS seed_nodes,
  CASE kc
    WHEN 'quyen_tham_nom' THEN
      [x IN collect(DISTINCT q) + collect(DISTINCT nv3) + collect(DISTINCT hv3)
       WHERE x IS NOT NULL]
    WHEN 'can_tro_tham_nom' THEN
      [x IN collect(DISTINCT hv_ct) + collect(DISTINCT nv83) + collect(DISTINCT q)
           + collect(DISTINCT nv3)
       WHERE x IS NOT NULL]
    WHEN 'xu_ly_hanh_vi_can_tro' THEN
      [x IN collect(DISTINCT hv_ct) + collect(DISTINCT nv83) WHERE x IS NOT NULL]
    WHEN 'lam_dung_tham_nom' THEN
      [x IN collect(DISTINCT hv_ld) + collect(DISTINCT dk_ld) + collect(DISTINCT qy)
           + collect(DISTINCT hv_yc) + collect(DISTINCT hq)
       WHERE x IS NOT NULL]
    WHEN 'yeu_cau_han_che_tham_nom' THEN
      [x IN collect(DISTINCT qy) + collect(DISTINCT hv_yc) + collect(DISTINCT hq)
       WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT q) + collect(DISTINCT nv3) + collect(DISTINCT hv_ct)
           + collect(DISTINCT nv83)
       WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: ThamNomVaCanTroThamNomParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "khia_canh_tham_nom": params.khia_canh_tham_nom,
        "chu_the_co_hanh_vi": params.chu_the_co_hanh_vi,
        "anh_huong_xau_den_con": params.anh_huong_xau_den_con,
        "whitelist_dieu_ids": _TONG_QUAT_WHITELIST if use_wl else [],
    }


tham_nom_va_can_tro_tham_nom = CypherTemplate(
    name="tham_nom_va_can_tro_tham_nom",
    description=(
        "Quyền, nghĩa vụ thăm nom của người không trực tiếp nuôi; cản trở của "
        "người trực tiếp nuôi hoặc thành viên gia đình; lạm dụng thăm nom và hạn chế. "
        "Không cấp dưỡng không tự làm mất quyền thăm nom. Ví dụ: có được ngăn cản cha "
        "gặp con; cản trở thăm nom bị xử lý thế nào; không cấp dưỡng có còn quyền thăm con."
    ),
    params_schema=ThamNomVaCanTroThamNomParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
