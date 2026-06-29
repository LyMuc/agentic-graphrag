"""Template — Vi phạm của văn phòng con nuôi nước ngoài tại Việt Nam Đ63 NĐ82."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from server.infrastructure.neo4j.cypher_templates.xu_phat_vi_pham._params_common import (
    KhiaCanhCheTai,
    KHIA_CANH_CHE_TAI_FIELD,
)
from server.infrastructure.neo4j.cypher_templates.xu_phat_vi_pham._seed_factory import make_parent_leaf_template

_LEAF_MAP: dict[str, str] = {
    "tay_xoa_ho_so": "tay_xoa_ho_so_giay_phep_van_phong_con_nuoi",
        "khong_thong_bao_cham_dut": "khong_thong_bao_cham_dut_van_phong_con_nuoi",
        "vi_pham_bao_cao_so_sach": "vi_pham_bao_cao_so_sach_van_phong_con_nuoi",
        "doi_nguoi_dung_dau_chua_phep": "thay_doi_nguoi_dung_dau_van_phong_con_nuoi_chua_duoc_phep",
        "gioi_thieu_tre_trai_luat": "gioi_thieu_tre_em_lam_con_nuoi_trai_phap_luat",
        "cho_muon_giay_phep": "cho_thue_muon_giay_phep_van_phong_con_nuoi",
        "dung_giay_phep_khac": "su_dung_giay_phep_van_phong_con_nuoi_khac",
        "khong_du_dieu_kien": "van_phong_con_nuoi_hoat_dong_khong_du_dieu_kien",
        "vi_pham_phi_loi_nhuan": "van_phong_con_nuoi_vi_pham_phi_loi_nhuan",
        "tong_quat": ""
}

_VPHC_WHITELIST = ['NghiDinh_82_2020_ND_CP_Dieu_63']
_HS_WHITELIST = []


class ViPhamVanPhongConNuoiNuocNgoaiParams(BaseModel):
    dang_hanh_vi: Literal["tay_xoa_ho_so","khong_thong_bao_cham_dut","vi_pham_bao_cao_so_sach","doi_nguoi_dung_dau_chua_phep","gioi_thieu_tre_trai_luat","cho_muon_giay_phep","dung_giay_phep_khac","khong_du_dieu_kien","vi_pham_phi_loi_nhuan","tong_quat"] = Field(description="Vi phạm văn phòng con nuôi nước ngoài Đ63.")
    khia_canh_che_tai: KhiaCanhCheTai = KHIA_CANH_CHE_TAI_FIELD


vi_pham_van_phong_con_nuoi_nuoc_ngoai = make_parent_leaf_template(
    name="vi_pham_van_phong_con_nuoi_nuoc_ngoai",
    description='Vi phạm của văn phòng con nuôi nước ngoài tại Việt Nam Đ63 NĐ82.',
    params_schema=ViPhamVanPhongConNuoiNuocNgoaiParams,
    parent_id="quy_dinh_van_phong_con_nuoi_nuoc_ngoai",
    router_field="dang_hanh_vi",
    leaf_map=_LEAF_MAP,
    vphc_whitelist=_VPHC_WHITELIST,
    hs_whitelist=_HS_WHITELIST or None,
    dual_che_tai=False,
    hs_only=False,
)
