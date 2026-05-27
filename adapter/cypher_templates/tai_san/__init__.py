"""Registry các Cypher template cho topic Tài sản (Điều 28-50 Luật HNGD 2014).

Được dùng bởi `adapter/retrievers/quan_he_giua_vo_va_chong/che_do_tai_san_cua_vo_chong_v3.py`.

8 template chính sách (KG ngữ nghĩa mới, schema xem `docs/kg_che_do_tai_san_schema.md`):
    1. phan_loai_tai_san — xác định tài sản chung/riêng (Đ33, Đ43, Đ40).
    2. nguyen_tac_che_do_tai_san — nguyên tắc Đ29-32 (áp dụng mọi chế độ).
    3. quyen_dinh_doat_tai_san — quyền định đoạt chung/riêng (Đ35, Đ44).
    4. dang_ky_quyen_so_huu_tai_san_chung — đăng ký GCN (Đ34).
    5. nghia_vu_tai_san — nghĩa vụ chung/riêng/liên đới (Đ27, Đ37, Đ45).
    6. chia_tai_san_thoi_ky_hon_nhan — chia tài sản trong hôn nhân (Đ38-42).
    7. thoa_thuan_che_do_tai_san — chế độ tài sản theo thỏa thuận (Đ47-50).
    8. tai_san_rieng_va_nha_o_duy_nhat — tài sản riêng & nhà ở duy nhất
       (Đ31, Đ43-46).
"""
from __future__ import annotations

from adapter.cypher_templates import TemplateRegistry

from adapter.cypher_templates.tai_san.phan_loai_tai_san import phan_loai_tai_san
from adapter.cypher_templates.tai_san.nguyen_tac_che_do_tai_san import (
    nguyen_tac_che_do_tai_san,
)
from adapter.cypher_templates.tai_san.quyen_dinh_doat_tai_san import (
    quyen_dinh_doat_tai_san,
)
from adapter.cypher_templates.tai_san.dang_ky_quyen_so_huu_tai_san_chung import (
    dang_ky_quyen_so_huu_tai_san_chung,
)
from adapter.cypher_templates.tai_san.nghia_vu_tai_san import nghia_vu_tai_san
from adapter.cypher_templates.tai_san.chia_tai_san_thoi_ky_hon_nhan import (
    chia_tai_san_thoi_ky_hon_nhan,
)
from adapter.cypher_templates.tai_san.thoa_thuan_che_do_tai_san import (
    thoa_thuan_che_do_tai_san,
)
from adapter.cypher_templates.tai_san.tai_san_rieng_va_nha_o_duy_nhat import (
    tai_san_rieng_va_nha_o_duy_nhat,
)


TAI_SAN_REGISTRY = TemplateRegistry(topic="tai_san")
TAI_SAN_REGISTRY.register(phan_loai_tai_san)
TAI_SAN_REGISTRY.register(nguyen_tac_che_do_tai_san)
TAI_SAN_REGISTRY.register(quyen_dinh_doat_tai_san)
TAI_SAN_REGISTRY.register(dang_ky_quyen_so_huu_tai_san_chung)
TAI_SAN_REGISTRY.register(nghia_vu_tai_san)
TAI_SAN_REGISTRY.register(chia_tai_san_thoi_ky_hon_nhan)
TAI_SAN_REGISTRY.register(thoa_thuan_che_do_tai_san)
TAI_SAN_REGISTRY.register(tai_san_rieng_va_nha_o_duy_nhat)


__all__ = [
    "TAI_SAN_REGISTRY",
    "phan_loai_tai_san",
    "nguyen_tac_che_do_tai_san",
    "quyen_dinh_doat_tai_san",
    "dang_ky_quyen_so_huu_tai_san_chung",
    "nghia_vu_tai_san",
    "chia_tai_san_thoi_ky_hon_nhan",
    "thoa_thuan_che_do_tai_san",
    "tai_san_rieng_va_nha_o_duy_nhat",
]
