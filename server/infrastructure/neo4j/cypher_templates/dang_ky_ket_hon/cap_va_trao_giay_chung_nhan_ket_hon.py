"""Template — cấp và trao Giấy chứng nhận kết hôn (Đ18 K2, Đ38 K3, NĐ123 Đ18 K3)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from server.infrastructure.neo4j.cypher_templates import CypherTemplate
from server.infrastructure.neo4j.cypher_templates.dang_ky_ket_hon._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("khia_canh_cap_trao",)
_DIEU_TRAO_WHITELIST = [
    "Luat_HoTich_2014_Dieu_18",
    "Luat_HoTich_2014_Dieu_38",
]


class CapVaTraoGiayChungNhanKetHonParams(BaseModel):
    khia_canh_cap_trao: Literal["to_chuc_trao", "so_ban_chinh", "ca_hai"] = Field(
        description=(
            "Lễ trao/tổ chức trao -> to_chuc_trao; mấy bản/bao nhiêu bản chính -> so_ban_chinh."
        )
    )
    cap_dang_ky: Literal["cap_xa", "cap_huyen", "xa_bien_gioi", "khong_ro"] = Field(
        description="Xã/phường -> cap_xa; huyện/quận -> cap_huyen."
    )
    yeu_to_nuoc_ngoai: Literal["co", "khong", "khong_ro"] = Field(
        description="Có người nước ngoài/Việt kiều -> co; hai công dân Việt Nam -> khong."
    )


_SEED_BODY = f"""
WITH $cap AS cap, $kc AS kc, $yn AS yn, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (ct_xa:ChuThe:{TOPIC_LABEL} {{id: 'chu_tich_ubnd_cap_xa', topic: '{TOPIC}'}})
WHERE kc IN ['to_chuc_trao', 'ca_hai'] AND cap IN ['cap_xa', 'khong_ro', 'xa_bien_gioi']
OPTIONAL MATCH (hv_trao:HanhVi:{TOPIC_LABEL} {{id: 'to_chuc_trao_giay_chung_nhan_ket_hon', topic: '{TOPIC}'}})
WHERE kc IN ['to_chuc_trao', 'ca_hai']

OPTIONAL MATCH (ct_huyen:ChuThe:{TOPIC_LABEL} {{id: 'chu_tich_ubnd_cap_huyen', topic: '{TOPIC}'}})
WHERE kc IN ['to_chuc_trao', 'ca_hai'] AND (cap IN ['cap_huyen', 'khong_ro'] OR yn = 'co')

OPTIONAL MATCH (q:Quyen:{TOPIC_LABEL} {{id: 'quyen_moi_ben_nhan_mot_ban_chinh', topic: '{TOPIC}'}})
WHERE kc IN ['so_ban_chinh', 'ca_hai']
OPTIONAL MATCH (hv_cap:HanhVi:{TOPIC_LABEL} {{id: 'cap_giay_chung_nhan_ket_hon', topic: '{TOPIC}'}})
WHERE kc IN ['so_ban_chinh', 'ca_hai']

WITH wl, kc,
  [x IN collect(DISTINCT ct_xa) + collect(DISTINCT ct_huyen)
       + collect(DISTINCT hv_trao) + collect(DISTINCT q) + collect(DISTINCT hv_cap)
   WHERE x IS NOT NULL] AS seed_nodes,
  CASE kc
    WHEN 'so_ban_chinh' THEN
      [x IN collect(DISTINCT q) + collect(DISTINCT hv_cap) WHERE x IS NOT NULL]
    WHEN 'to_chuc_trao' THEN
      [x IN collect(DISTINCT hv_trao) + collect(DISTINCT ct_xa) + collect(DISTINCT ct_huyen)
       WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT hv_trao) + collect(DISTINCT q) WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: CapVaTraoGiayChungNhanKetHonParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "cap": params.cap_dang_ky,
        "kc": params.khia_canh_cap_trao,
        "yn": params.yeu_to_nuoc_ngoai,
        "whitelist_dieu_ids": _DIEU_TRAO_WHITELIST if use_wl else [],
    }


cap_va_trao_giay_chung_nhan_ket_hon = CypherTemplate(
    name="cap_va_trao_giay_chung_nhan_ket_hon",
    description=(
        "Xử lý giai đoạn đầu ra: ký/cấp, tổ chức trao Giấy chứng nhận và số bản chính "
        "mỗi bên nhận (Đ18 K2, Đ38 K3, NĐ123 Đ18 K3). "
        "Ví dụ: Có được tổ chức lễ trao Giấy chứng nhận kết hôn không?; "
        "Mỗi bên được cấp mấy bản chính Giấy chứng nhận kết hôn?"
    ),
    params_schema=CapVaTraoGiayChungNhanKetHonParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
