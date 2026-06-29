"""Template — giải quyết tài sản khi chung sống (Đ16 K1-2)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from server.infrastructure.neo4j.cypher_templates import CypherTemplate
from server.infrastructure.neo4j.cypher_templates.chung_song_nhu_vo_chong._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("khia_canh_tai_san",)
_DIEU_16_WHITELIST = ["Luat_HNGD_2014_Dieu_16"]


class GiaiQuyetTaiSanKhiChungSongParams(BaseModel):
    co_thoa_thuan: Literal["co", "khong", "khong_ro"] = Field(
        description="Đã thỏa thuận -> co; không thỏa thuận -> khong; không nêu -> khong_ro."
    )
    khia_canh_tai_san: Literal[
        "nguyen_tac_giai_quyet",
        "chia_tai_san",
        "bao_ve_phu_nu_va_con",
        "cong_suc_noi_tro",
        "tong_quat",
    ] = Field(
        description=(
            "Chia tài sản -> chia_tai_san; nguyên tắc -> nguyen_tac_giai_quyet; "
            "bảo vệ phụ nữ/con -> bao_ve_phu_nu_va_con; nội trợ -> cong_suc_noi_tro."
        )
    )


_SEED_BODY = f"""
WITH $ct AS ct, $kc AS kc, $whitelist_dieu_ids AS wl

MATCH (hv:HanhVi:{TOPIC_LABEL} {{id: 'giai_quyet_quan_he_tai_san', topic: '{TOPIC}'}})

OPTIONAL MATCH (tt:ThoaThuan:{TOPIC_LABEL} {{id: 'thoa_thuan_tai_san_nghia_vu_hop_dong', topic: '{TOPIC}'}})
WHERE ct IN ['co', 'khong_ro']
OPTIONAL MATCH (dk_co:DieuKien:{TOPIC_LABEL} {{id: 'co_thoa_thuan_giua_cac_ben', topic: '{TOPIC}'}})
WHERE tt IS NOT NULL
OPTIONAL MATCH (hq_co:HauQua:{TOPIC_LABEL} {{id: 'ap_dung_thoa_thuan_giua_cac_ben', topic: '{TOPIC}'}})
WHERE tt IS NOT NULL

OPTIONAL MATCH (dk_khong:DieuKien:{TOPIC_LABEL} {{id: 'khong_co_thoa_thuan_giua_cac_ben', topic: '{TOPIC}'}})
WHERE ct IN ['khong', 'khong_ro']
OPTIONAL MATCH (hq_bl:HauQua:{TOPIC_LABEL} {{id: 'ap_dung_bo_luat_dan_su_va_phap_luat_lien_quan', topic: '{TOPIC}'}})
WHERE dk_khong IS NOT NULL

OPTIONAL MATCH (hq_bv:HauQua:{TOPIC_LABEL} {{id: 'bao_dam_quyen_loi_hop_phap_cua_phu_nu_va_con', topic: '{TOPIC}'}})
WHERE kc IN ['bao_ve_phu_nu_va_con', 'chia_tai_san', 'tong_quat']
OPTIONAL MATCH (hv_nt:HanhVi:{TOPIC_LABEL} {{id: 'thuc_hien_cong_viec_noi_tro_duy_tri_doi_song_chung', topic: '{TOPIC}'}})
WHERE kc IN ['cong_suc_noi_tro', 'chia_tai_san', 'tong_quat']
OPTIONAL MATCH (hq_nt:HauQua:{TOPIC_LABEL} {{id: 'cong_viec_noi_tro_duoc_coi_nhu_lao_dong_co_thu_nhap', topic: '{TOPIC}'}})
WHERE hv_nt IS NOT NULL

WITH wl, ct, kc,
  [x IN collect(DISTINCT hv) + collect(DISTINCT tt) + collect(DISTINCT dk_co)
       + collect(DISTINCT hq_co) + collect(DISTINCT dk_khong) + collect(DISTINCT hq_bl)
       + collect(DISTINCT hq_bv) + collect(DISTINCT hv_nt) + collect(DISTINCT hq_nt)
   WHERE x IS NOT NULL] AS seed_nodes,
  CASE ct
    WHEN 'co' THEN
      [x IN collect(DISTINCT tt) + collect(DISTINCT dk_co) + collect(DISTINCT hq_co)
       WHERE x IS NOT NULL]
    WHEN 'khong' THEN
      [x IN collect(DISTINCT dk_khong) + collect(DISTINCT hq_bl) WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT tt) + collect(DISTINCT dk_co) + collect(DISTINCT hq_co)
           + collect(DISTINCT dk_khong) + collect(DISTINCT hq_bl)
       WHERE x IS NOT NULL]
  END AS leaf_base,
  [x IN collect(DISTINCT hq_bv) + collect(DISTINCT hv_nt) + collect(DISTINCT hq_nt)
   WHERE x IS NOT NULL] AS leaf_extra

WITH wl, seed_nodes, leaf_base + leaf_extra AS leaf_seed_nodes
"""


def _params_builder(params: GiaiQuyetTaiSanKhiChungSongParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "ct": params.co_thoa_thuan,
        "kc": params.khia_canh_tai_san,
        "whitelist_dieu_ids": _DIEU_16_WHITELIST if use_wl else [],
    }


giai_quyet_tai_san_khi_chung_song = CypherTemplate(
    name="giai_quyet_tai_san_khi_chung_song",
    description=(
        "Giải quyết tài sản giữa các bên chung sống không đăng ký: ưu tiên thỏa thuận, "
        "không có thì áp dụng BLDS; bảo vệ phụ nữ/con và tính công việc nội trợ (Đ16). "
        "Ví dụ: Nam nữ sống như vợ chồng không đăng ký chia tài sản chung như thế nào; "
        "Phân chia tài sản trong thời gian sống thử."
    ),
    params_schema=GiaiQuyetTaiSanKhiChungSongParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
