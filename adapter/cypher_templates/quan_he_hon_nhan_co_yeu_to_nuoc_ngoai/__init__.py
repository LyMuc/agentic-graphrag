"""Registry các Cypher template cho topic quan_he_hon_nhan_co_yeu_to_nuoc_ngoai."""
from __future__ import annotations

from adapter.cypher_templates import TemplateRegistry

from adapter.cypher_templates.quan_he_hon_nhan_co_yeu_to_nuoc_ngoai.ap_dung_phap_luat_yeu_to_nuoc_ngoai import (
    ap_dung_phap_luat_yeu_to_nuoc_ngoai,
)
from adapter.cypher_templates.quan_he_hon_nhan_co_yeu_to_nuoc_ngoai.bao_ve_quyen_loi_yeu_to_nuoc_ngoai import (
    bao_ve_quyen_loi_yeu_to_nuoc_ngoai,
)
from adapter.cypher_templates.quan_he_hon_nhan_co_yeu_to_nuoc_ngoai.cap_duong_co_yeu_to_nuoc_ngoai import (
    cap_duong_co_yeu_to_nuoc_ngoai,
)
from adapter.cypher_templates.quan_he_hon_nhan_co_yeu_to_nuoc_ngoai.cong_nhan_ghi_chu_ban_an_nuoc_ngoai import (
    cong_nhan_ghi_chu_ban_an_nuoc_ngoai,
)
from adapter.cypher_templates.quan_he_hon_nhan_co_yeu_to_nuoc_ngoai.hop_phap_hoa_lanh_su_giay_to import (
    hop_phap_hoa_lanh_su_giay_to,
)
from adapter.cypher_templates.quan_he_hon_nhan_co_yeu_to_nuoc_ngoai.ket_hon_co_yeu_to_nuoc_ngoai import (
    ket_hon_co_yeu_to_nuoc_ngoai,
)
from adapter.cypher_templates.quan_he_hon_nhan_co_yeu_to_nuoc_ngoai.ly_hon_co_yeu_to_nuoc_ngoai import (
    ly_hon_co_yeu_to_nuoc_ngoai,
)
from adapter.cypher_templates.quan_he_hon_nhan_co_yeu_to_nuoc_ngoai.tham_quyen_vu_viec_yeu_to_nuoc_ngoai import (
    tham_quyen_vu_viec_yeu_to_nuoc_ngoai,
)
from adapter.cypher_templates.quan_he_hon_nhan_co_yeu_to_nuoc_ngoai.tai_san_thoa_thuan_va_chung_song_khong_dang_ky import (
    tai_san_thoa_thuan_va_chung_song_khong_dang_ky,
)
from adapter.cypher_templates.quan_he_hon_nhan_co_yeu_to_nuoc_ngoai.xac_dinh_cha_me_con_co_yeu_to_nuoc_ngoai import (
    xac_dinh_cha_me_con_co_yeu_to_nuoc_ngoai,
)


QUAN_HE_HON_NHAN_CO_YEU_TO_NUOC_NGOAI_REGISTRY = TemplateRegistry(
    topic="quan_he_hon_nhan_co_yeu_to_nuoc_ngoai"
)
QUAN_HE_HON_NHAN_CO_YEU_TO_NUOC_NGOAI_REGISTRY.register(bao_ve_quyen_loi_yeu_to_nuoc_ngoai)
QUAN_HE_HON_NHAN_CO_YEU_TO_NUOC_NGOAI_REGISTRY.register(ap_dung_phap_luat_yeu_to_nuoc_ngoai)
QUAN_HE_HON_NHAN_CO_YEU_TO_NUOC_NGOAI_REGISTRY.register(tham_quyen_vu_viec_yeu_to_nuoc_ngoai)
QUAN_HE_HON_NHAN_CO_YEU_TO_NUOC_NGOAI_REGISTRY.register(hop_phap_hoa_lanh_su_giay_to)
QUAN_HE_HON_NHAN_CO_YEU_TO_NUOC_NGOAI_REGISTRY.register(cong_nhan_ghi_chu_ban_an_nuoc_ngoai)
QUAN_HE_HON_NHAN_CO_YEU_TO_NUOC_NGOAI_REGISTRY.register(ket_hon_co_yeu_to_nuoc_ngoai)
QUAN_HE_HON_NHAN_CO_YEU_TO_NUOC_NGOAI_REGISTRY.register(ly_hon_co_yeu_to_nuoc_ngoai)
QUAN_HE_HON_NHAN_CO_YEU_TO_NUOC_NGOAI_REGISTRY.register(xac_dinh_cha_me_con_co_yeu_to_nuoc_ngoai)
QUAN_HE_HON_NHAN_CO_YEU_TO_NUOC_NGOAI_REGISTRY.register(cap_duong_co_yeu_to_nuoc_ngoai)
QUAN_HE_HON_NHAN_CO_YEU_TO_NUOC_NGOAI_REGISTRY.register(tai_san_thoa_thuan_va_chung_song_khong_dang_ky)


__all__ = [
    "QUAN_HE_HON_NHAN_CO_YEU_TO_NUOC_NGOAI_REGISTRY",
    "bao_ve_quyen_loi_yeu_to_nuoc_ngoai",
    "ap_dung_phap_luat_yeu_to_nuoc_ngoai",
    "tham_quyen_vu_viec_yeu_to_nuoc_ngoai",
    "hop_phap_hoa_lanh_su_giay_to",
    "cong_nhan_ghi_chu_ban_an_nuoc_ngoai",
    "ket_hon_co_yeu_to_nuoc_ngoai",
    "ly_hon_co_yeu_to_nuoc_ngoai",
    "xac_dinh_cha_me_con_co_yeu_to_nuoc_ngoai",
    "cap_duong_co_yeu_to_nuoc_ngoai",
    "tai_san_thoa_thuan_va_chung_song_khong_dang_ky",
]
