"""Template — giải quyết tài sản khi một bên chết/tuyên bố đã chết (Đ66)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.hon_nhan_cham_dut_do_vo_chong_chet._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("khia_canh_tai_san",)
_DIEU_66_WHITELIST = ["Luat_HNGD_2014_Dieu_66"]


class GiaiQuyetTaiSanKhiMotBenChetParams(BaseModel):
    su_kien: Literal[
        "chet_thuc_te",
        "bi_tuyen_bo_da_chet",
        "mot_ben_chet_hoac_bi_tuyen_bo_da_chet",
        "khong_ro",
    ] = Field(description="Ngữ cảnh sự kiện; cả hai nhánh đều áp dụng Điều 66.")
    khia_canh_tai_san: Literal[
        "quan_ly_tai_san_chung",
        "nguoi_quan_ly_di_san",
        "chia_tai_san_va_di_san",
        "han_che_phan_chia_di_san",
        "tai_san_trong_kinh_doanh",
        "tong_quat",
    ] = Field(description="Khía cạnh quyết định khoản 1-4 được seed.")
    co_yeu_cau_chia_di_san: Literal["co", "khong", "khong_ro"] = Field(
        description="Có yêu cầu chia di sản → seed khoản 2."
    )
    co_thoa_thuan_che_do_tai_san: Literal["co", "khong", "khong_ro"] = Field(
        description="Có thỏa thuận chế độ tài sản → seed ngoại lệ chia đôi."
    )
    anh_huong_nghiem_trong_den_doi_song: Literal["co", "khong", "khong_ro"] = Field(
        description="Ảnh hưởng nghiêm trọng → seed khoản 3."
    )


_SEED_BODY = f"""
WITH $kc AS kc, $chia AS chia, $thoa AS thoa, $anh_huong AS ah, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (ct:ChuThe:{TOPIC_LABEL} {{id: 'vo_hoac_chong_con_song_sau_khi_ben_kia_chet', topic: '{TOPIC}'}})
WHERE kc IN ['quan_ly_tai_san_chung', 'nguoi_quan_ly_di_san', 'tong_quat', 'khong_ro']
OPTIONAL MATCH (q_ql:Quyen:{TOPIC_LABEL} {{id: 'quyen_ben_con_song_quan_ly_tai_san_chung', topic: '{TOPIC}'}})
WHERE kc IN ['quan_ly_tai_san_chung', 'nguoi_quan_ly_di_san', 'tong_quat']
OPTIONAL MATCH (hv_ql:HanhVi:{TOPIC_LABEL} {{id: 'ben_con_song_quan_ly_tai_san_chung', topic: '{TOPIC}'}})
WHERE kc IN ['quan_ly_tai_san_chung', 'nguoi_quan_ly_di_san', 'tong_quat']
OPTIONAL MATCH (ts_chung:LoaiTaiSan:{TOPIC_LABEL} {{id: 'tai_san_chung_khi_mot_ben_chet', topic: '{TOPIC}'}})
WHERE hv_ql IS NOT NULL
OPTIONAL MATCH (dk_dc:DieuKien:{TOPIC_LABEL} {{id: 'di_chuc_chi_dinh_nguoi_khac_quan_ly_di_san', topic: '{TOPIC}'}})
WHERE kc = 'nguoi_quan_ly_di_san'
OPTIONAL MATCH (dk_tt:DieuKien:{TOPIC_LABEL} {{id: 'nguoi_thua_ke_thoa_thuan_cu_nguoi_khac_quan_ly_di_san', topic: '{TOPIC}'}})
WHERE kc = 'nguoi_quan_ly_di_san'

OPTIONAL MATCH (dk_chia:DieuKien:{TOPIC_LABEL} {{id: 'co_yeu_cau_chia_di_san', topic: '{TOPIC}'}})
WHERE kc IN ['chia_tai_san_va_di_san', 'tong_quat'] OR chia = 'co'
OPTIONAL MATCH (hv_chia:HanhVi:{TOPIC_LABEL} {{id: 'chia_tai_san_chung_khi_co_yeu_cau_chia_di_san', topic: '{TOPIC}'}})
WHERE dk_chia IS NOT NULL OR kc = 'chia_tai_san_va_di_san'
OPTIONAL MATCH (hq_chia:HauQua:{TOPIC_LABEL} {{id: 'tai_san_chung_duoc_chia_doi_tru_thoa_thuan', topic: '{TOPIC}'}})
WHERE hv_chia IS NOT NULL
OPTIONAL MATCH (tt_cs:ThoaThuan:{TOPIC_LABEL} {{id: 'thoa_thuan_che_do_tai_san_ap_dung_khi_chia_di_san', topic: '{TOPIC}'}})
WHERE thoa = 'co' OR kc = 'chia_tai_san_va_di_san'
OPTIONAL MATCH (hv_thua_ke:HanhVi:{TOPIC_LABEL} {{id: 'chia_phan_tai_san_cua_nguoi_chet_theo_phap_luat_thua_ke', topic: '{TOPIC}'}})
WHERE kc IN ['chia_tai_san_va_di_san', 'tong_quat'] OR chia = 'co'
OPTIONAL MATCH (ts_chet:LoaiTaiSan:{TOPIC_LABEL} {{id: 'phan_tai_san_cua_nguoi_chet_trong_tai_san_chung', topic: '{TOPIC}'}})
WHERE hv_thua_ke IS NOT NULL
OPTIONAL MATCH (hq_thua_ke:HauQua:{TOPIC_LABEL} {{id: 'phan_tai_san_nguoi_chet_duoc_chia_theo_phap_luat_thua_ke', topic: '{TOPIC}'}})
WHERE hv_thua_ke IS NOT NULL

OPTIONAL MATCH (dk_hc:DieuKien:{TOPIC_LABEL} {{id: 'chia_di_san_anh_huong_nghiem_trong_den_doi_song', topic: '{TOPIC}'}})
WHERE kc = 'han_che_phan_chia_di_san' OR ah = 'co'
OPTIONAL MATCH (q_hc:Quyen:{TOPIC_LABEL} {{id: 'quyen_yeu_cau_toa_an_han_che_phan_chia_di_san', topic: '{TOPIC}'}})
WHERE dk_hc IS NOT NULL
OPTIONAL MATCH (hv_hc:HanhVi:{TOPIC_LABEL} {{id: 'yeu_cau_toa_an_han_che_phan_chia_di_san', topic: '{TOPIC}'}})
WHERE q_hc IS NOT NULL
OPTIONAL MATCH (hq_hc:HauQua:{TOPIC_LABEL} {{id: 'toa_an_co_the_han_che_phan_chia_di_san', topic: '{TOPIC}'}})
WHERE hv_hc IS NOT NULL

OPTIONAL MATCH (hv_kd:HanhVi:{TOPIC_LABEL} {{id: 'giai_quyet_tai_san_vo_chong_trong_kinh_doanh', topic: '{TOPIC}'}})
WHERE kc = 'tai_san_trong_kinh_doanh'
OPTIONAL MATCH (ts_kd:LoaiTaiSan:{TOPIC_LABEL} {{id: 'tai_san_vo_chong_trong_kinh_doanh_khi_mot_ben_chet', topic: '{TOPIC}'}})
WHERE hv_kd IS NOT NULL

WITH wl, kc,
  [x IN collect(DISTINCT ct) + collect(DISTINCT q_ql) + collect(DISTINCT hv_ql)
       + collect(DISTINCT ts_chung) + collect(DISTINCT dk_dc) + collect(DISTINCT dk_tt)
       + collect(DISTINCT dk_chia) + collect(DISTINCT hv_chia) + collect(DISTINCT hq_chia)
       + collect(DISTINCT tt_cs) + collect(DISTINCT hv_thua_ke) + collect(DISTINCT ts_chet)
       + collect(DISTINCT hq_thua_ke) + collect(DISTINCT dk_hc) + collect(DISTINCT q_hc)
       + collect(DISTINCT hv_hc) + collect(DISTINCT hq_hc)
       + collect(DISTINCT hv_kd) + collect(DISTINCT ts_kd)
   WHERE x IS NOT NULL] AS seed_nodes,
  CASE kc
    WHEN 'quan_ly_tai_san_chung' THEN
      [x IN collect(DISTINCT q_ql) + collect(DISTINCT hv_ql) + collect(DISTINCT ts_chung)
       WHERE x IS NOT NULL]
    WHEN 'nguoi_quan_ly_di_san' THEN
      [x IN collect(DISTINCT hv_ql) + collect(DISTINCT dk_dc) + collect(DISTINCT dk_tt)
       WHERE x IS NOT NULL]
    WHEN 'chia_tai_san_va_di_san' THEN
      [x IN collect(DISTINCT hv_chia) + collect(DISTINCT hq_chia) + collect(DISTINCT hv_thua_ke)
           + collect(DISTINCT hq_thua_ke)
       WHERE x IS NOT NULL]
    WHEN 'han_che_phan_chia_di_san' THEN
      [x IN collect(DISTINCT q_hc) + collect(DISTINCT hv_hc) + collect(DISTINCT hq_hc)
       WHERE x IS NOT NULL]
    WHEN 'tai_san_trong_kinh_doanh' THEN
      [x IN collect(DISTINCT hv_kd) + collect(DISTINCT ts_kd) WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT hv_ql) + collect(DISTINCT hv_chia) + collect(DISTINCT hv_hc)
           + collect(DISTINCT hv_kd)
       WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: GiaiQuyetTaiSanKhiMotBenChetParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "kc": params.khia_canh_tai_san,
        "chia": params.co_yeu_cau_chia_di_san,
        "thoa": params.co_thoa_thuan_che_do_tai_san,
        "anh_huong": params.anh_huong_nghiem_trong_den_doi_song,
        "whitelist_dieu_ids": _DIEU_66_WHITELIST if use_wl else [],
    }


giai_quyet_tai_san_khi_mot_ben_chet = CypherTemplate(
    name="giai_quyet_tai_san_khi_mot_ben_chet",
    description=(
        "Truy xuất Điều 66 về quản lý tài sản chung, chia tài sản khi có yêu cầu "
        "chia di sản, quyền yêu cầu hạn chế phân chia và tài sản dùng trong kinh doanh. "
        "Ví dụ: Khi một bên vợ chồng chết thì bên còn sống có được quản lý tài sản chung không?; "
        "Một bên vợ chồng chết hoặc bị tòa án tuyên bố đã chết thì tài sản chung được "
        "giải quyết như thế nào?"
    ),
    params_schema=GiaiQuyetTaiSanKhiMotBenChetParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
