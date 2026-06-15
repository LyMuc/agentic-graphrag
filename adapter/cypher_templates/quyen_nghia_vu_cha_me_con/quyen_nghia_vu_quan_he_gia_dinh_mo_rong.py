"""Template — quyền, nghĩa vụ quan hệ gia đình mở rộng cùng sống chung (Đ79-80)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.quyen_nghia_vu_cha_me_con._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("loai_quan_he_gia_dinh_mo_rong",)
_DIEU_WHITELIST_79 = ["Luat_HNGD_2014_Dieu_79"]
_DIEU_WHITELIST_80 = ["Luat_HNGD_2014_Dieu_80"]


class QuyenNghiaVuQuanHeGiaDinhMoRongParams(BaseModel):
    loai_quan_he_gia_dinh_mo_rong: Literal[
        "cha_duong_me_ke_va_con_rieng",
        "con_dau_re_va_cha_me_vo_chong",
        "khong_ro",
    ] = Field(description="cha dượng/mẹ kế -> Đ79; con dâu/rể -> Đ80.")
    chieu_quyen_nghia_vu: Literal[
        "nguoi_lon_doi_voi_con_rieng",
        "con_rieng_doi_voi_cha_duong_me_ke",
        "hai_ben_lan_nhau",
        "tong_quat",
    ] = Field(description="đối với nhau -> hai_ben_lan_nhau.")
    tinh_trang_song_chung: Literal[
        "co_song_chung",
        "khong_song_chung",
        "khong_ro",
    ] = Field(description="sống chung là điều kiện bắt buộc của Đ79-80.")


_SEED_BODY = f"""
WITH $loai AS loai, $chieu AS chieu, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (qh79:QuanHe:{TOPIC_LABEL} {{
  id: 'quan_he_cha_duong_me_ke_con_rieng_cung_song_chung', topic: '{TOPIC}'
}})
WHERE loai IN ['cha_duong_me_ke_va_con_rieng', 'khong_ro']
  OR chieu IN ['nguoi_lon_doi_voi_con_rieng', 'con_rieng_doi_voi_cha_duong_me_ke', 'hai_ben_lan_nhau']

OPTIONAL MATCH (nv79_1:NghiaVu:{TOPIC_LABEL} {{
  id: 'cha_duong_me_ke_cham_soc_giao_duc_con_rieng', topic: '{TOPIC}'
}})
WHERE loai = 'cha_duong_me_ke_va_con_rieng'
  AND chieu IN ['nguoi_lon_doi_voi_con_rieng', 'hai_ben_lan_nhau', 'khong_ro']

OPTIONAL MATCH (nv79_2:NghiaVu:{TOPIC_LABEL} {{
  id: 'con_rieng_cham_soc_phung_duong_cha_duong_me_ke', topic: '{TOPIC}'
}})
WHERE loai = 'cha_duong_me_ke_va_con_rieng'
  AND chieu IN ['con_rieng_doi_voi_cha_duong_me_ke', 'hai_ben_lan_nhau', 'khong_ro']

OPTIONAL MATCH (qh80:QuanHe:{TOPIC_LABEL} {{
  id: 'quan_he_con_dau_re_cha_me_vo_chong_cung_song_chung', topic: '{TOPIC}'
}})
WHERE loai IN ['con_dau_re_va_cha_me_vo_chong', 'khong_ro']
  OR chieu = 'hai_ben_lan_nhau'

OPTIONAL MATCH (nv80:NghiaVu:{TOPIC_LABEL} {{
  id: 'cac_ben_ton_trong_quan_tam_cham_soc_giup_do_nhau', topic: '{TOPIC}'
}})
WHERE loai = 'con_dau_re_va_cha_me_vo_chong'
  AND chieu IN ['hai_ben_lan_nhau', 'khong_ro']

WITH wl, loai, chieu,
  collect(DISTINCT qh79) + collect(DISTINCT nv79_1) + collect(DISTINCT nv79_2)
    + collect(DISTINCT qh80) + collect(DISTINCT nv80)
    AS seed_nodes,
  [x IN collect(DISTINCT qh79) + collect(DISTINCT nv79_1) + collect(DISTINCT nv79_2)
        + collect(DISTINCT qh80) + collect(DISTINCT nv80)
   WHERE x IS NOT NULL] AS leaf_seed_nodes
"""


def _params_builder(params: QuyenNghiaVuQuanHeGiaDinhMoRongParams) -> dict[str, Any]:
    loai = params.loai_quan_he_gia_dinh_mo_rong
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    wl: list[str] = []
    if use_wl:
        if loai == "cha_duong_me_ke_va_con_rieng":
            wl = _DIEU_WHITELIST_79
        elif loai == "con_dau_re_va_cha_me_vo_chong":
            wl = _DIEU_WHITELIST_80
        elif loai == "khong_ro":
            wl = _DIEU_WHITELIST_79 + _DIEU_WHITELIST_80
    return {
        "loai": loai,
        "chieu": params.chieu_quyen_nghia_vu,
        "whitelist_dieu_ids": wl,
    }


quyen_nghia_vu_quan_he_gia_dinh_mo_rong = CypherTemplate(
    name="quyen_nghia_vu_quan_he_gia_dinh_mo_rong",
    description=(
        "Trả lời hai quan hệ cùng có điều kiện sống chung: cha dượng/mẹ kế với con riêng tại Điều 79, "
        "và con dâu/con rể với cha mẹ chồng/cha mẹ vợ tại Điều 80. "
        "Dùng khi hỏi quyền nghĩa vụ cha dượng/mẹ kế và con riêng đối với nhau, "
        "hoặc con dâu/con rể sống chung với cha mẹ chồng/vợ."
    ),
    params_schema=QuyenNghiaVuQuanHeGiaDinhMoRongParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
