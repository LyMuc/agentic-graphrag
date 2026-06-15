"""Registry các Cypher template cho topic quyen_nghia_vu_cha_me_con."""
from __future__ import annotations

from adapter.cypher_templates import TemplateRegistry

from adapter.cypher_templates.quyen_nghia_vu_cha_me_con.bao_ve_quyen_nghia_vu_cha_me_con import (
    bao_ve_quyen_nghia_vu_cha_me_con,
)
from adapter.cypher_templates.quyen_nghia_vu_cha_me_con.nghia_vu_quyen_cua_cha_me import (
    nghia_vu_quyen_cua_cha_me,
)
from adapter.cypher_templates.quyen_nghia_vu_cha_me_con.quyen_nghia_vu_cua_con import (
    quyen_nghia_vu_cua_con,
)
from adapter.cypher_templates.quyen_nghia_vu_cha_me_con.cham_soc_nuoi_duong_giua_cha_me_con import (
    cham_soc_nuoi_duong_giua_cha_me_con,
)
from adapter.cypher_templates.quyen_nghia_vu_cha_me_con.giao_duc_con import (
    giao_duc_con,
)
from adapter.cypher_templates.quyen_nghia_vu_cha_me_con.dai_dien_va_giao_dich_cho_con import (
    dai_dien_va_giao_dich_cho_con,
)
from adapter.cypher_templates.quyen_nghia_vu_cha_me_con.boi_thuong_thiet_hai_do_con_gay_ra import (
    boi_thuong_thiet_hai_do_con_gay_ra,
)
from adapter.cypher_templates.quyen_nghia_vu_cha_me_con.quyen_nghia_vu_cha_me_nuoi_con_nuoi import (
    quyen_nghia_vu_cha_me_nuoi_con_nuoi,
)
from adapter.cypher_templates.quyen_nghia_vu_cha_me_con.quyen_nghia_vu_quan_he_gia_dinh_mo_rong import (
    quyen_nghia_vu_quan_he_gia_dinh_mo_rong,
)


QUYEN_NGHIA_VU_CHA_ME_CON_REGISTRY = TemplateRegistry(
    topic="quyen_nghia_vu_cha_me_con"
)
QUYEN_NGHIA_VU_CHA_ME_CON_REGISTRY.register(bao_ve_quyen_nghia_vu_cha_me_con)
QUYEN_NGHIA_VU_CHA_ME_CON_REGISTRY.register(nghia_vu_quyen_cua_cha_me)
QUYEN_NGHIA_VU_CHA_ME_CON_REGISTRY.register(quyen_nghia_vu_cua_con)
QUYEN_NGHIA_VU_CHA_ME_CON_REGISTRY.register(cham_soc_nuoi_duong_giua_cha_me_con)
QUYEN_NGHIA_VU_CHA_ME_CON_REGISTRY.register(giao_duc_con)
QUYEN_NGHIA_VU_CHA_ME_CON_REGISTRY.register(dai_dien_va_giao_dich_cho_con)
QUYEN_NGHIA_VU_CHA_ME_CON_REGISTRY.register(boi_thuong_thiet_hai_do_con_gay_ra)
QUYEN_NGHIA_VU_CHA_ME_CON_REGISTRY.register(quyen_nghia_vu_cha_me_nuoi_con_nuoi)
QUYEN_NGHIA_VU_CHA_ME_CON_REGISTRY.register(quyen_nghia_vu_quan_he_gia_dinh_mo_rong)


__all__ = [
    "QUYEN_NGHIA_VU_CHA_ME_CON_REGISTRY",
    "bao_ve_quyen_nghia_vu_cha_me_con",
    "nghia_vu_quyen_cua_cha_me",
    "quyen_nghia_vu_cua_con",
    "cham_soc_nuoi_duong_giua_cha_me_con",
    "giao_duc_con",
    "dai_dien_va_giao_dich_cho_con",
    "boi_thuong_thiet_hai_do_con_gay_ra",
    "quyen_nghia_vu_cha_me_nuoi_con_nuoi",
    "quyen_nghia_vu_quan_he_gia_dinh_mo_rong",
]
