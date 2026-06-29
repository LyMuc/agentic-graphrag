"""Registry các Cypher template cho topic cha_me_con_sau_ly_hon (Đ81-84)."""
from __future__ import annotations

from server.infrastructure.neo4j.cypher_templates import TemplateRegistry

from server.infrastructure.neo4j.cypher_templates.cha_me_con_sau_ly_hon.quyen_nghia_vu_chung_sau_ly_hon import (
    quyen_nghia_vu_chung_sau_ly_hon,
)
from server.infrastructure.neo4j.cypher_templates.cha_me_con_sau_ly_hon.xac_dinh_nguoi_truc_tiep_nuoi_con import (
    xac_dinh_nguoi_truc_tiep_nuoi_con,
)
from server.infrastructure.neo4j.cypher_templates.cha_me_con_sau_ly_hon.nuoi_con_duoi_36_thang import (
    nuoi_con_duoi_36_thang,
)
from server.infrastructure.neo4j.cypher_templates.cha_me_con_sau_ly_hon.quyen_nghia_vu_nguoi_khong_truc_tiep_nuoi import (
    quyen_nghia_vu_nguoi_khong_truc_tiep_nuoi,
)
from server.infrastructure.neo4j.cypher_templates.cha_me_con_sau_ly_hon.tham_nom_va_can_tro_tham_nom import (
    tham_nom_va_can_tro_tham_nom,
)
from server.infrastructure.neo4j.cypher_templates.cha_me_con_sau_ly_hon.thay_doi_nguoi_truc_tiep_nuoi_con import (
    thay_doi_nguoi_truc_tiep_nuoi_con,
)


CHA_ME_CON_SAU_LY_HON_REGISTRY = TemplateRegistry(topic="cha_me_con_sau_ly_hon")
CHA_ME_CON_SAU_LY_HON_REGISTRY.register(quyen_nghia_vu_chung_sau_ly_hon)
CHA_ME_CON_SAU_LY_HON_REGISTRY.register(xac_dinh_nguoi_truc_tiep_nuoi_con)
CHA_ME_CON_SAU_LY_HON_REGISTRY.register(nuoi_con_duoi_36_thang)
CHA_ME_CON_SAU_LY_HON_REGISTRY.register(quyen_nghia_vu_nguoi_khong_truc_tiep_nuoi)
CHA_ME_CON_SAU_LY_HON_REGISTRY.register(tham_nom_va_can_tro_tham_nom)
CHA_ME_CON_SAU_LY_HON_REGISTRY.register(thay_doi_nguoi_truc_tiep_nuoi_con)


__all__ = [
    "CHA_ME_CON_SAU_LY_HON_REGISTRY",
    "quyen_nghia_vu_chung_sau_ly_hon",
    "xac_dinh_nguoi_truc_tiep_nuoi_con",
    "nuoi_con_duoi_36_thang",
    "quyen_nghia_vu_nguoi_khong_truc_tiep_nuoi",
    "tham_nom_va_can_tro_tham_nom",
    "thay_doi_nguoi_truc_tiep_nuoi_con",
]
