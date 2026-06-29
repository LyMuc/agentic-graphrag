"""Registry các Cypher template cho topic tai_san_rieng_cua_con."""
from __future__ import annotations

from server.infrastructure.neo4j.cypher_templates import TemplateRegistry

from server.infrastructure.neo4j.cypher_templates.tai_san_rieng_cua_con.xac_dinh_tai_san_rieng_cua_con import (
    xac_dinh_tai_san_rieng_cua_con,
)
from server.infrastructure.neo4j.cypher_templates.tai_san_rieng_cua_con.nghia_vu_dong_gop_thu_nhap_cua_con import (
    nghia_vu_dong_gop_thu_nhap_cua_con,
)
from server.infrastructure.neo4j.cypher_templates.tai_san_rieng_cua_con.quan_ly_tai_san_con_tu_du_15_tuoi import (
    quan_ly_tai_san_con_tu_du_15_tuoi,
)
from server.infrastructure.neo4j.cypher_templates.tai_san_rieng_cua_con.quan_ly_tai_san_con_duoi_15_hoac_mat_nang_luc import (
    quan_ly_tai_san_con_duoi_15_hoac_mat_nang_luc,
)
from server.infrastructure.neo4j.cypher_templates.tai_san_rieng_cua_con.cha_me_khong_quan_ly_hoac_chuyen_giao_cho_nguoi_khac import (
    cha_me_khong_quan_ly_hoac_chuyen_giao_cho_nguoi_khac,
)
from server.infrastructure.neo4j.cypher_templates.tai_san_rieng_cua_con.dinh_doat_tai_san_con_duoi_15_tuoi import (
    dinh_doat_tai_san_con_duoi_15_tuoi,
)
from server.infrastructure.neo4j.cypher_templates.tai_san_rieng_cua_con.dinh_doat_tai_san_con_tu_du_15_den_duoi_18_tuoi import (
    dinh_doat_tai_san_con_tu_du_15_den_duoi_18_tuoi,
)
from server.infrastructure.neo4j.cypher_templates.tai_san_rieng_cua_con.dinh_doat_tai_san_con_thanh_nien_mat_nang_luc import (
    dinh_doat_tai_san_con_thanh_nien_mat_nang_luc,
)


TAI_SAN_RIENG_CUA_CON_REGISTRY = TemplateRegistry(topic="tai_san_rieng_cua_con")
TAI_SAN_RIENG_CUA_CON_REGISTRY.register(xac_dinh_tai_san_rieng_cua_con)
TAI_SAN_RIENG_CUA_CON_REGISTRY.register(nghia_vu_dong_gop_thu_nhap_cua_con)
TAI_SAN_RIENG_CUA_CON_REGISTRY.register(quan_ly_tai_san_con_tu_du_15_tuoi)
TAI_SAN_RIENG_CUA_CON_REGISTRY.register(quan_ly_tai_san_con_duoi_15_hoac_mat_nang_luc)
TAI_SAN_RIENG_CUA_CON_REGISTRY.register(cha_me_khong_quan_ly_hoac_chuyen_giao_cho_nguoi_khac)
TAI_SAN_RIENG_CUA_CON_REGISTRY.register(dinh_doat_tai_san_con_duoi_15_tuoi)
TAI_SAN_RIENG_CUA_CON_REGISTRY.register(dinh_doat_tai_san_con_tu_du_15_den_duoi_18_tuoi)
TAI_SAN_RIENG_CUA_CON_REGISTRY.register(dinh_doat_tai_san_con_thanh_nien_mat_nang_luc)


__all__ = [
    "TAI_SAN_RIENG_CUA_CON_REGISTRY",
    "xac_dinh_tai_san_rieng_cua_con",
    "nghia_vu_dong_gop_thu_nhap_cua_con",
    "quan_ly_tai_san_con_tu_du_15_tuoi",
    "quan_ly_tai_san_con_duoi_15_hoac_mat_nang_luc",
    "cha_me_khong_quan_ly_hoac_chuyen_giao_cho_nguoi_khac",
    "dinh_doat_tai_san_con_duoi_15_tuoi",
    "dinh_doat_tai_san_con_tu_du_15_den_duoi_18_tuoi",
    "dinh_doat_tai_san_con_thanh_nien_mat_nang_luc",
]
