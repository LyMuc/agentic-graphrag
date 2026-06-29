"""Registry các Cypher template cho topic xac_dinh_cha_me_con (Đ88-93, 99, 101-102)."""
from __future__ import annotations

from server.infrastructure.neo4j.cypher_templates import TemplateRegistry

from server.infrastructure.neo4j.cypher_templates.xac_dinh_cha_me_con.xac_dinh_con_chung_theo_hon_nhan import (
    xac_dinh_con_chung_theo_hon_nhan,
)
from server.infrastructure.neo4j.cypher_templates.xac_dinh_cha_me_con.yeu_cau_xac_dinh_con_tai_toa_an import (
    yeu_cau_xac_dinh_con_tai_toa_an,
)
from server.infrastructure.neo4j.cypher_templates.xac_dinh_cha_me_con.quyen_nhan_cha_me_con import (
    quyen_nhan_cha_me_con,
)
from server.infrastructure.neo4j.cypher_templates.xac_dinh_cha_me_con.xac_dinh_khi_nguoi_yeu_cau_da_chet import (
    xac_dinh_khi_nguoi_yeu_cau_da_chet,
)
from server.infrastructure.neo4j.cypher_templates.xac_dinh_cha_me_con.xac_dinh_cha_me_bang_ho_tro_sinh_san import (
    xac_dinh_cha_me_bang_ho_tro_sinh_san,
)
from server.infrastructure.neo4j.cypher_templates.xac_dinh_cha_me_con.giai_quyet_tranh_chap_ho_tro_sinh_san_mang_thai_ho import (
    giai_quyet_tranh_chap_ho_tro_sinh_san_mang_thai_ho,
)
from server.infrastructure.neo4j.cypher_templates.xac_dinh_cha_me_con.tham_quyen_xac_dinh_cha_me_con import (
    tham_quyen_xac_dinh_cha_me_con,
)
from server.infrastructure.neo4j.cypher_templates.xac_dinh_cha_me_con.nguoi_co_quyen_yeu_cau_xac_dinh_cha_me_con import (
    nguoi_co_quyen_yeu_cau_xac_dinh_cha_me_con,
)


XAC_DINH_CHA_ME_CON_REGISTRY = TemplateRegistry(topic="xac_dinh_cha_me_con")
XAC_DINH_CHA_ME_CON_REGISTRY.register(xac_dinh_con_chung_theo_hon_nhan)
XAC_DINH_CHA_ME_CON_REGISTRY.register(yeu_cau_xac_dinh_con_tai_toa_an)
XAC_DINH_CHA_ME_CON_REGISTRY.register(quyen_nhan_cha_me_con)
XAC_DINH_CHA_ME_CON_REGISTRY.register(xac_dinh_khi_nguoi_yeu_cau_da_chet)
XAC_DINH_CHA_ME_CON_REGISTRY.register(xac_dinh_cha_me_bang_ho_tro_sinh_san)
XAC_DINH_CHA_ME_CON_REGISTRY.register(giai_quyet_tranh_chap_ho_tro_sinh_san_mang_thai_ho)
XAC_DINH_CHA_ME_CON_REGISTRY.register(tham_quyen_xac_dinh_cha_me_con)
XAC_DINH_CHA_ME_CON_REGISTRY.register(nguoi_co_quyen_yeu_cau_xac_dinh_cha_me_con)


__all__ = [
    "XAC_DINH_CHA_ME_CON_REGISTRY",
    "xac_dinh_con_chung_theo_hon_nhan",
    "yeu_cau_xac_dinh_con_tai_toa_an",
    "quyen_nhan_cha_me_con",
    "xac_dinh_khi_nguoi_yeu_cau_da_chet",
    "xac_dinh_cha_me_bang_ho_tro_sinh_san",
    "giai_quyet_tranh_chap_ho_tro_sinh_san_mang_thai_ho",
    "tham_quyen_xac_dinh_cha_me_con",
    "nguoi_co_quyen_yeu_cau_xac_dinh_cha_me_con",
]
