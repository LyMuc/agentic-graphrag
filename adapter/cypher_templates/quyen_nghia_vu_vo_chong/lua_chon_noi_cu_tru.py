"""Template — lựa chọn nơi cư trú vợ chồng (Đ20 + Đ14 Luật Cư trú)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.quyen_nghia_vu_vo_chong._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
)


class LuaChonNoiCuTruParams(BaseModel):
    tinh_huong_cu_tru: Literal[
        "chuyen_khau_ve_nha_chong",
        "o_chung_gia_dinh_chong",
        "chong_tu_quyet_noi_cu_tru",
        "phong_tuc_tap_quan_va_dia_gioi_hanh_chinh",
        "noi_cu_tru_khac_nhau",
        "noi_thuong_xuyen_chung_song",
        "khong_ro",
    ] = Field(description="chuyển khẩu về nhà chồng -> chuyen_khau_ve_nha_chong; chồng quyết định -> chong_tu_quyet_noi_cu_tru.")
    khia_canh_cu_tru: Literal[
        "ai_quyet_dinh",
        "co_bat_buoc",
        "co_duoc_o_khac_nhau",
        "xac_dinh_noi_cu_tru",
        "co_bi_rang_buoc",
        "tong_quat",
        "khong_ro",
    ] = Field(description="do ai quyết định -> ai_quyet_dinh; có bắt buộc -> co_bat_buoc.")


_SEED_BODY = f"""
WITH $th AS th, $kc AS kc,
     $seed_thoa_thuan AS seed_thoa_thuan, $seed_chong_tu_quyet AS seed_chong_tu_quyet,
     $seed_phong_tuc AS seed_phong_tuc, $seed_noi_chung AS seed_noi_chung,
     $seed_khac_nhau AS seed_khac_nhau, $seed_bat_buoc AS seed_bat_buoc,
     $whitelist_dieu_ids AS wl

OPTIONAL MATCH (qd_thoa:QuyDinh:{TOPIC_LABEL} {{
  id: 'lua_chon_noi_cu_tru_do_vo_chong_thoa_thuan', topic: '{TOPIC}'
}})
WHERE seed_thoa_thuan = true OR seed_phong_tuc = true OR seed_chong_tu_quyet = true

OPTIONAL MATCH (q:Quyen:{TOPIC_LABEL} {{id: 'quyen_thoa_thuan_noi_cu_tru', topic: '{TOPIC}'}})
WHERE seed_thoa_thuan = true OR seed_chong_tu_quyet = true

OPTIONAL MATCH (hv_cq:HanhVi:{TOPIC_LABEL} {{
  id: 'chong_tu_quyet_noi_cu_tru', topic: '{TOPIC}'
}})
WHERE seed_chong_tu_quyet = true

OPTIONAL MATCH (qd_noi:QuyDinh:{TOPIC_LABEL} {{
  id: 'noi_cu_tru_vo_chong_la_noi_thuong_xuyen_chung_song', topic: '{TOPIC}'
}})
WHERE seed_noi_chung = true

OPTIONAL MATCH (qd_khac:QuyDinh:{TOPIC_LABEL} {{
  id: 'vo_chong_co_the_co_noi_cu_tru_khac_nhau', topic: '{TOPIC}'
}})
WHERE seed_khac_nhau = true
OPTIONAL MATCH (dk_khac:DieuKien:{TOPIC_LABEL} {{
  id: 'thoa_thuan_noi_cu_tru_khac_nhau', topic: '{TOPIC}'
}})
WHERE seed_khac_nhau = true

OPTIONAL MATCH (hv_khau:HanhVi:{TOPIC_LABEL} {{
  id: 'bat_buoc_vo_chuyen_khau_ve_nha_chong', topic: '{TOPIC}'
}})
WHERE seed_bat_buoc = true AND th = 'chuyen_khau_ve_nha_chong'
OPTIONAL MATCH (qd_khau:QuyDinh:{TOPIC_LABEL} {{
  id: 'khong_bat_buoc_vo_chuyen_khau_ve_nha_chong', topic: '{TOPIC}'
}})
WHERE seed_bat_buoc = true AND th = 'chuyen_khau_ve_nha_chong'

OPTIONAL MATCH (hv_gd:HanhVi:{TOPIC_LABEL} {{
  id: 'bat_buoc_vo_o_chung_gia_dinh_chong', topic: '{TOPIC}'
}})
WHERE seed_bat_buoc = true AND th = 'o_chung_gia_dinh_chong'
OPTIONAL MATCH (qd_gd:QuyDinh:{TOPIC_LABEL} {{
  id: 'khong_bat_buoc_vo_o_chung_gia_dinh_chong', topic: '{TOPIC}'
}})
WHERE seed_bat_buoc = true AND th = 'o_chung_gia_dinh_chong'

WITH wl, th,
  collect(DISTINCT qd_thoa) + collect(DISTINCT q) + collect(DISTINCT hv_cq)
    + collect(DISTINCT qd_noi) + collect(DISTINCT qd_khac) + collect(DISTINCT dk_khac)
    + collect(DISTINCT hv_khau) + collect(DISTINCT qd_khau)
    + collect(DISTINCT hv_gd) + collect(DISTINCT qd_gd)
    AS seed_nodes,
  [x IN collect(DISTINCT qd_thoa) + collect(DISTINCT q) + collect(DISTINCT hv_cq)
       + collect(DISTINCT qd_noi) + collect(DISTINCT qd_khac) + collect(DISTINCT dk_khac)
       + collect(DISTINCT hv_khau) + collect(DISTINCT qd_khau)
       + collect(DISTINCT hv_gd) + collect(DISTINCT qd_gd)
   WHERE x IS NOT NULL] AS leaf_seed_nodes
"""


def _params_builder(params: LuaChonNoiCuTruParams) -> dict[str, Any]:
    th = params.tinh_huong_cu_tru
    kc = params.khia_canh_cu_tru
    seed_thoa_thuan = th in (
        "chong_tu_quyet_noi_cu_tru",
        "phong_tuc_tap_quan_va_dia_gioi_hanh_chinh",
        "chuyen_khau_ve_nha_chong",
        "o_chung_gia_dinh_chong",
        "khong_ro",
    ) or kc in ("ai_quyet_dinh", "co_bi_rang_buoc", "tong_quat")
    seed_chong_tu_quyet = th == "chong_tu_quyet_noi_cu_tru"
    seed_phong_tuc = th == "phong_tuc_tap_quan_va_dia_gioi_hanh_chinh"
    seed_noi_chung = th == "noi_thuong_xuyen_chung_song" or kc == "xac_dinh_noi_cu_tru"
    seed_khac_nhau = th == "noi_cu_tru_khac_nhau" or kc == "co_duoc_o_khac_nhau"
    seed_bat_buoc = th in ("chuyen_khau_ve_nha_chong", "o_chung_gia_dinh_chong") or kc == "co_bat_buoc"
    return {
        "th": th,
        "kc": kc,
        "seed_thoa_thuan": seed_thoa_thuan,
        "seed_chong_tu_quyet": seed_chong_tu_quyet,
        "seed_phong_tuc": seed_phong_tuc,
        "seed_noi_chung": seed_noi_chung,
        "seed_khac_nhau": seed_khac_nhau,
        "seed_bat_buoc": seed_bat_buoc,
        "whitelist_dieu_ids": [],
    }


lua_chon_noi_cu_tru = CypherTemplate(
    name="lua_chon_noi_cu_tru",
    description=(
        "Trả lời ai quyết định nơi cư trú, ảnh hưởng phong tục/địa giới, việc chuyển hộ khẩu "
        "hoặc ở chung gia đình chồng và khả năng vợ chồng có nơi cư trú khác nhau. "
        "Kết hợp Điều 20 Luật HNGD với Điều 14 Luật Cư trú khi cần. "
        "Ví dụ: Vợ có phải chuyển khẩu về nhà chồng sau kết hôn?; "
        "Chồng có quyền tự quyết nơi cư trú?; "
        "Vợ có bắt buộc ở chung với gia đình chồng?"
    ),
    params_schema=LuaChonNoiCuTruParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
