"""Index tập trung mọi TemplateRegistry — dùng cho graph_viz và tooling."""
from __future__ import annotations

from server.infrastructure.neo4j.cypher_templates import TemplateRegistry
from server.infrastructure.neo4j.cypher_templates.cap_duong import CAP_DUONG_REGISTRY
from server.infrastructure.neo4j.cypher_templates.cha_me_con_sau_ly_hon import CHA_ME_CON_SAU_LY_HON_REGISTRY
from server.infrastructure.neo4j.cypher_templates.chia_tai_san_sau_ly_hon import CHIA_TAI_SAN_SAU_LY_HON_REGISTRY
from server.infrastructure.neo4j.cypher_templates.chung_song_nhu_vo_chong import CHUNG_SONG_NHU_VO_CHONG_REGISTRY
from server.infrastructure.neo4j.cypher_templates.dang_ky_ket_hon import DANG_KY_KET_HON_REGISTRY
from server.infrastructure.neo4j.cypher_templates.dieu_kien_ket_hon import DIEU_KIEN_KET_HON_REGISTRY
from server.infrastructure.neo4j.cypher_templates.ket_hon_trai_phap_luat import KET_HON_TRAI_PHAP_LUAT_REGISTRY
from server.infrastructure.neo4j.cypher_templates.han_che_quyen_cha_me_con_chua_thanh_nien import (
    HAN_CHE_QUYEN_CHA_ME_CON_CHUA_THANH_NIEN_REGISTRY,
)
from server.infrastructure.neo4j.cypher_templates.quy_dinh_chung_khai_niem_phap_ly import (
    QUY_DINH_CHUNG_KHAI_NIEM_PHAP_LY_REGISTRY,
)
from server.infrastructure.neo4j.cypher_templates.quy_dinh_chung_ly_hon import QUY_DINH_CHUNG_LY_HON_REGISTRY
from server.infrastructure.neo4j.cypher_templates.hon_nhan_cham_dut_do_vo_chong_chet import (
    HON_NHAN_CHAM_DUT_DO_VO_CHONG_CHET_REGISTRY,
)
from server.infrastructure.neo4j.cypher_templates.quan_he_hon_nhan_co_yeu_to_nuoc_ngoai import QUAN_HE_HON_NHAN_CO_YEU_TO_NUOC_NGOAI_REGISTRY
from server.infrastructure.neo4j.cypher_templates.quan_he_giua_cac_thanh_vien_khac_trong_gia_dinh import (
    QUAN_HE_GIUA_CAC_THANH_VIEN_KHAC_TRONG_GIA_DINH_REGISTRY,
)
from server.infrastructure.neo4j.cypher_templates.quyen_nghia_vu_vo_chong import (
    QUYEN_NGHIA_VU_VO_CHONG_REGISTRY,
)
from server.infrastructure.neo4j.cypher_templates.quyen_nghia_vu_cha_me_con import (
    QUYEN_NGHIA_VU_CHA_ME_CON_REGISTRY,
)
from server.infrastructure.neo4j.cypher_templates.dai_dien_trach_nhiem_vo_chong import (
    DAI_DIEN_TRACH_NHIEM_VO_CHONG_REGISTRY,
)
from server.infrastructure.neo4j.cypher_templates.xac_dinh_cha_me_con import (
    XAC_DINH_CHA_ME_CON_REGISTRY,
)
from server.infrastructure.neo4j.cypher_templates.xu_phat_vi_pham import XU_PHAT_VI_PHAM_REGISTRY
from server.infrastructure.neo4j.cypher_templates.tai_san import TAI_SAN_REGISTRY
from server.infrastructure.neo4j.cypher_templates.tai_san_rieng_cua_con import (
    TAI_SAN_RIENG_CUA_CON_REGISTRY,
)

_ALL: tuple[TemplateRegistry, ...] = (
    TAI_SAN_REGISTRY,
    TAI_SAN_RIENG_CUA_CON_REGISTRY,
    CHIA_TAI_SAN_SAU_LY_HON_REGISTRY,
    DANG_KY_KET_HON_REGISTRY,
    DIEU_KIEN_KET_HON_REGISTRY,
    KET_HON_TRAI_PHAP_LUAT_REGISTRY,
    HAN_CHE_QUYEN_CHA_ME_CON_CHUA_THANH_NIEN_REGISTRY,
    QUY_DINH_CHUNG_KHAI_NIEM_PHAP_LY_REGISTRY,
    QUY_DINH_CHUNG_LY_HON_REGISTRY,
    HON_NHAN_CHAM_DUT_DO_VO_CHONG_CHET_REGISTRY,
    CHUNG_SONG_NHU_VO_CHONG_REGISTRY,
    CHA_ME_CON_SAU_LY_HON_REGISTRY,
    CAP_DUONG_REGISTRY,
    QUAN_HE_HON_NHAN_CO_YEU_TO_NUOC_NGOAI_REGISTRY,
    QUAN_HE_GIUA_CAC_THANH_VIEN_KHAC_TRONG_GIA_DINH_REGISTRY,
    QUYEN_NGHIA_VU_VO_CHONG_REGISTRY,
    DAI_DIEN_TRACH_NHIEM_VO_CHONG_REGISTRY,
    QUYEN_NGHIA_VU_CHA_ME_CON_REGISTRY,
    XAC_DINH_CHA_ME_CON_REGISTRY,
    XU_PHAT_VI_PHAM_REGISTRY,
)

ALL_TEMPLATE_REGISTRIES: dict[str, TemplateRegistry] = {
    reg.topic: reg for reg in _ALL
}

__all__ = ["ALL_TEMPLATE_REGISTRIES"]
