"""Registry các Cypher template cho topic hon_nhan_cham_dut_do_vo_chong_chet (Đ65-67)."""
from __future__ import annotations

from server.infrastructure.neo4j.cypher_templates import TemplateRegistry

from server.infrastructure.neo4j.cypher_templates.hon_nhan_cham_dut_do_vo_chong_chet.thoi_diem_cham_dut_hon_nhan_do_chet import (
    thoi_diem_cham_dut_hon_nhan_do_chet,
)
from server.infrastructure.neo4j.cypher_templates.hon_nhan_cham_dut_do_vo_chong_chet.giai_quyet_tai_san_khi_mot_ben_chet import (
    giai_quyet_tai_san_khi_mot_ben_chet,
)
from server.infrastructure.neo4j.cypher_templates.hon_nhan_cham_dut_do_vo_chong_chet.khoi_phuc_quan_he_hon_nhan_khi_nguoi_bi_tuyen_bo_da_chet_tro_ve import (
    khoi_phuc_quan_he_hon_nhan_khi_nguoi_bi_tuyen_bo_da_chet_tro_ve,
)
from server.infrastructure.neo4j.cypher_templates.hon_nhan_cham_dut_do_vo_chong_chet.giai_quyet_tai_san_khi_nguoi_bi_tuyen_bo_da_chet_tro_ve import (
    giai_quyet_tai_san_khi_nguoi_bi_tuyen_bo_da_chet_tro_ve,
)


HON_NHAN_CHAM_DUT_DO_VO_CHONG_CHET_REGISTRY = TemplateRegistry(
    topic="hon_nhan_cham_dut_do_vo_chong_chet"
)
HON_NHAN_CHAM_DUT_DO_VO_CHONG_CHET_REGISTRY.register(thoi_diem_cham_dut_hon_nhan_do_chet)
HON_NHAN_CHAM_DUT_DO_VO_CHONG_CHET_REGISTRY.register(giai_quyet_tai_san_khi_mot_ben_chet)
HON_NHAN_CHAM_DUT_DO_VO_CHONG_CHET_REGISTRY.register(
    khoi_phuc_quan_he_hon_nhan_khi_nguoi_bi_tuyen_bo_da_chet_tro_ve
)
HON_NHAN_CHAM_DUT_DO_VO_CHONG_CHET_REGISTRY.register(
    giai_quyet_tai_san_khi_nguoi_bi_tuyen_bo_da_chet_tro_ve
)


__all__ = [
    "HON_NHAN_CHAM_DUT_DO_VO_CHONG_CHET_REGISTRY",
    "thoi_diem_cham_dut_hon_nhan_do_chet",
    "giai_quyet_tai_san_khi_mot_ben_chet",
    "khoi_phuc_quan_he_hon_nhan_khi_nguoi_bi_tuyen_bo_da_chet_tro_ve",
    "giai_quyet_tai_san_khi_nguoi_bi_tuyen_bo_da_chet_tro_ve",
]
