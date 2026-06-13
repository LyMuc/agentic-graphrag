"""Index tập trung mọi TemplateRegistry — dùng cho graph_viz và tooling."""
from __future__ import annotations

from adapter.cypher_templates import TemplateRegistry
from adapter.cypher_templates.cap_duong import CAP_DUONG_REGISTRY
from adapter.cypher_templates.cha_me_con_sau_ly_hon import CHA_ME_CON_SAU_LY_HON_REGISTRY
from adapter.cypher_templates.chia_tai_san_sau_ly_hon import CHIA_TAI_SAN_SAU_LY_HON_REGISTRY
from adapter.cypher_templates.chung_song_nhu_vo_chong import CHUNG_SONG_NHU_VO_CHONG_REGISTRY
from adapter.cypher_templates.dang_ky_ket_hon import DANG_KY_KET_HON_REGISTRY
from adapter.cypher_templates.dieu_kien_ket_hon import DIEU_KIEN_KET_HON_REGISTRY
from adapter.cypher_templates.han_che_quyen_cha_me_con_chua_thanh_nien import (
    HAN_CHE_QUYEN_CHA_ME_CON_CHUA_THANH_NIEN_REGISTRY,
)
from adapter.cypher_templates.quy_dinh_chung_ly_hon import QUY_DINH_CHUNG_LY_HON_REGISTRY
from adapter.cypher_templates.hon_nhan_cham_dut_do_vo_chong_chet import (
    HON_NHAN_CHAM_DUT_DO_VO_CHONG_CHET_REGISTRY,
)
from adapter.cypher_templates.tai_san import TAI_SAN_REGISTRY

_ALL: tuple[TemplateRegistry, ...] = (
    TAI_SAN_REGISTRY,
    CHIA_TAI_SAN_SAU_LY_HON_REGISTRY,
    DANG_KY_KET_HON_REGISTRY,
    DIEU_KIEN_KET_HON_REGISTRY,
    HAN_CHE_QUYEN_CHA_ME_CON_CHUA_THANH_NIEN_REGISTRY,
    QUY_DINH_CHUNG_LY_HON_REGISTRY,
    HON_NHAN_CHAM_DUT_DO_VO_CHONG_CHET_REGISTRY,
    CHUNG_SONG_NHU_VO_CHONG_REGISTRY,
    CHA_ME_CON_SAU_LY_HON_REGISTRY,
    CAP_DUONG_REGISTRY,
)

ALL_TEMPLATE_REGISTRIES: dict[str, TemplateRegistry] = {
    reg.topic: reg for reg in _ALL
}

__all__ = ["ALL_TEMPLATE_REGISTRIES"]
