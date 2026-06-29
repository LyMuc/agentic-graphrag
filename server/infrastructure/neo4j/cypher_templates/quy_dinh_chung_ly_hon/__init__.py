"""Registry các Cypher template cho topic quy_dinh_chung_ly_hon (Đ51-57)."""
from __future__ import annotations

from server.infrastructure.neo4j.cypher_templates import TemplateRegistry

from server.infrastructure.neo4j.cypher_templates.quy_dinh_chung_ly_hon.quyen_yeu_cau_va_han_che_ly_hon import (
    quyen_yeu_cau_va_han_che_ly_hon,
)
from server.infrastructure.neo4j.cypher_templates.quy_dinh_chung_ly_hon.hoa_giai_va_thu_ly_ly_hon import (
    hoa_giai_va_thu_ly_ly_hon,
)
from server.infrastructure.neo4j.cypher_templates.quy_dinh_chung_ly_hon.dieu_kien_thuan_tinh_ly_hon import (
    dieu_kien_thuan_tinh_ly_hon,
)
from server.infrastructure.neo4j.cypher_templates.quy_dinh_chung_ly_hon.xac_dinh_hinh_thuc_ly_hon import (
    xac_dinh_hinh_thuc_ly_hon,
)
from server.infrastructure.neo4j.cypher_templates.quy_dinh_chung_ly_hon.can_cu_don_phuong_ly_hon import (
    can_cu_don_phuong_ly_hon,
)
from server.infrastructure.neo4j.cypher_templates.quy_dinh_chung_ly_hon.ly_hon_khi_mat_tich_hoac_khong_lien_lac import (
    ly_hon_khi_mat_tich_hoac_khong_lien_lac,
)
from server.infrastructure.neo4j.cypher_templates.quy_dinh_chung_ly_hon.thoi_diem_cham_dut_hon_nhan import (
    thoi_diem_cham_dut_hon_nhan,
)


QUY_DINH_CHUNG_LY_HON_REGISTRY = TemplateRegistry(topic="quy_dinh_chung_ly_hon")
QUY_DINH_CHUNG_LY_HON_REGISTRY.register(quyen_yeu_cau_va_han_che_ly_hon)
QUY_DINH_CHUNG_LY_HON_REGISTRY.register(hoa_giai_va_thu_ly_ly_hon)
QUY_DINH_CHUNG_LY_HON_REGISTRY.register(dieu_kien_thuan_tinh_ly_hon)
QUY_DINH_CHUNG_LY_HON_REGISTRY.register(xac_dinh_hinh_thuc_ly_hon)
QUY_DINH_CHUNG_LY_HON_REGISTRY.register(can_cu_don_phuong_ly_hon)
QUY_DINH_CHUNG_LY_HON_REGISTRY.register(ly_hon_khi_mat_tich_hoac_khong_lien_lac)
QUY_DINH_CHUNG_LY_HON_REGISTRY.register(thoi_diem_cham_dut_hon_nhan)


__all__ = [
    "QUY_DINH_CHUNG_LY_HON_REGISTRY",
    "quyen_yeu_cau_va_han_che_ly_hon",
    "hoa_giai_va_thu_ly_ly_hon",
    "dieu_kien_thuan_tinh_ly_hon",
    "xac_dinh_hinh_thuc_ly_hon",
    "can_cu_don_phuong_ly_hon",
    "ly_hon_khi_mat_tich_hoac_khong_lien_lac",
    "thoi_diem_cham_dut_hon_nhan",
]
