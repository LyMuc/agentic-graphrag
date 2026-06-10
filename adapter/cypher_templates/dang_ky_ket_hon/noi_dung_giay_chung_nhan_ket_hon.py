"""Template — nội dung Giấy chứng nhận kết hôn (Đ17 K2, Luật Hộ tịch 2024 Đ4 K7)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.dang_ky_ket_hon._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("khia_canh_noi_dung",)
_DIEU_17_WHITELIST = ["Luat_HoTich_2014_Dieu_17"]

_NOI_DUNG_MAP = {
    "dinh_nghia_giay": ["giay_chung_nhan_ket_hon"],
    "thong_tin_nhan_than": ["thong_tin_nhan_than_hai_ben_tren_giay"],
    "ngay_dang_ky": ["ngay_thang_nam_dang_ky_tren_giay"],
    "chu_ky_xac_nhan": ["chu_ky_diem_chi_va_xac_nhan_tren_giay"],
    "tat_ca": [
        "thong_tin_nhan_than_hai_ben_tren_giay",
        "ngay_thang_nam_dang_ky_tren_giay",
        "chu_ky_diem_chi_va_xac_nhan_tren_giay",
    ],
}


class NoiDungGiayChungNhanKetHonParams(BaseModel):
    khia_canh_noi_dung: Literal[
        "dinh_nghia_giay",
        "thong_tin_nhan_than",
        "ngay_dang_ky",
        "chu_ky_xac_nhan",
        "tat_ca",
    ] = Field(
        description=(
            "Giấy chứng nhận là gì -> dinh_nghia_giay; họ tên/ngày sinh/quốc tịch "
            "-> thong_tin_nhan_than; ngày đăng ký -> ngay_dang_ky; chữ ký/điểm chỉ "
            "-> chu_ky_xac_nhan; gồm thông tin gì -> tat_ca."
        )
    )


_SEED_BODY = f"""
WITH $kc AS kc, $part_ids AS part_ids, $whitelist_dieu_ids AS wl

MATCH (gcn:GiayToHoTich:{TOPIC_LABEL} {{id: 'giay_chung_nhan_ket_hon', topic: '{TOPIC}'}})

OPTIONAL MATCH (gcn)-[:CO_NOI_DUNG]->(part:GiayToHoTich:{TOPIC_LABEL})
WHERE part.id IN part_ids AND part.topic = '{TOPIC}'

WITH wl, kc,
  [x IN collect(DISTINCT gcn) + collect(DISTINCT part) WHERE x IS NOT NULL] AS seed_nodes,
  CASE kc
    WHEN 'dinh_nghia_giay' THEN
      [x IN collect(DISTINCT gcn) WHERE x IS NOT NULL]
    WHEN 'tat_ca' THEN
      [x IN collect(DISTINCT part) WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT part) WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: NoiDungGiayChungNhanKetHonParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    part_ids = _NOI_DUNG_MAP.get(params.khia_canh_noi_dung, _NOI_DUNG_MAP["tat_ca"])
    return {
        "kc": params.khia_canh_noi_dung,
        "part_ids": part_ids,
        "whitelist_dieu_ids": _DIEU_17_WHITELIST if use_wl else [],
    }


noi_dung_giay_chung_nhan_ket_hon = CypherTemplate(
    name="noi_dung_giay_chung_nhan_ket_hon",
    description=(
        "Trả lời định nghĩa và các trường thông tin bắt buộc trên Giấy chứng nhận kết hôn: "
        "nhân thân hai bên, ngày đăng ký, chữ ký/điểm chỉ và xác nhận cơ quan (Đ17 K2). "
        "Ví dụ: Giấy chứng nhận kết hôn gồm những thông tin gì?; "
        "Nội dung bắt buộc trên Giấy chứng nhận kết hôn?"
    ),
    params_schema=NoiDungGiayChungNhanKetHonParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
