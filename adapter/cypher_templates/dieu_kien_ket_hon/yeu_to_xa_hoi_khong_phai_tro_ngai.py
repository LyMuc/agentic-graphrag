"""Template — yếu tố xã hội không phải trở ngại nội dung (Đ8, Đ5)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.dieu_kien_ket_hon._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("khia_canh_yeu_to_xa_hoi",)
_DIEU_WHITELIST = ["Luat_HNGD_2014_Dieu_5", "Luat_HNGD_2014_Dieu_8"]

_YEU_TO_QD: dict[str, str] = {
    "khac_tin_nguong_gia_dinh_phan_doi": "khac_tin_nguong_khong_tu_dong_la_tro_ngai_ket_hon",
    "ho_khau_sau_ly_hon": "ho_khau_khong_phai_dieu_kien_noi_dung_ket_hon",
    "quan_he_giao_vien_hoc_sinh": "quan_he_giao_vien_hoc_sinh_khong_tu_dong_quyet_dinh",
    "xung_khac_tuoi": "xung_khac_tuoi_khong_phai_dieu_kien_luat_dinh",
}


class YeuToXaHoiKhongPhaiTroNgaiParams(BaseModel):
    yeu_to_xa_hoi: Literal[
        "khac_tin_nguong_gia_dinh_phan_doi",
        "ho_khau_sau_ly_hon",
        "quan_he_giao_vien_hoc_sinh",
        "xung_khac_tuoi",
        "khong_ro",
    ] = Field(
        description=(
            "khác đạo/tín ngưỡng -> khac_tin_nguong_gia_dinh_phan_doi; "
            "chưa cắt khẩu -> ho_khau_sau_ly_hon; "
            "giáo viên-học sinh -> quan_he_giao_vien_hoc_sinh; "
            "khắc tuổi -> xung_khac_tuoi."
        )
    )
    tinh_trang_hon_nhan_hien_tai: Literal[
        "da_ly_hon",
        "dang_co_vo_chong",
        "chua_co_vo_chong",
        "khong_ro",
    ] = Field(
        description=(
            "đã ly hôn -> da_ly_hon; "
            "chưa ly hôn/đang có chồng -> dang_co_vo_chong; "
            "độc thân -> chua_co_vo_chong."
        )
    )
    co_du_tuoi_ro_rang: Literal["co", "khong", "khong_ro"] = Field(
        description=(
            "tuổi cụ thể đủ ngưỡng -> co; "
            "tuổi dưới ngưỡng -> khong; chỉ nói học sinh -> khong_ro."
        )
    )
    khia_canh_yeu_to_xa_hoi: Literal[
        "co_phai_tro_ngai",
        "co_duoc_ket_hon",
        "dieu_kien_can_kiem_tra",
        "tong_quat",
    ] = Field(
        description=(
            "có lấy nhau được không -> co_duoc_ket_hon; "
            "có phải trở ngại không -> co_phai_tro_ngai; "
            "cần kiểm tra gì -> dieu_kien_can_kiem_tra."
        )
    )


_SEED_BODY = f"""
WITH $yt AS yt, $qd_id AS qd_id, $tthn AS tthn, $kc AS kc,
     $seed_tuoi AS seed_tuoi, $seed_dk AS seed_dk, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (qd:QuyDinh:{TOPIC_LABEL} {{id: qd_id, topic: '{TOPIC}'}})
WHERE qd_id <> ''

OPTIONAL MATCH (dk_tn:DieuKien:{TOPIC_LABEL} {{
  id: 'hai_ben_tu_nguyen_quyet_dinh', topic: '{TOPIC}'
}})
WHERE yt = 'khac_tin_nguong_gia_dinh_phan_doi'
OPTIONAL MATCH (qd_gd:QuyDinh:{TOPIC_LABEL} {{
  id: 'gia_dinh_khong_dong_y_khong_thay_the_y_chi_hai_ben', topic: '{TOPIC}'
}})
WHERE yt = 'khac_tin_nguong_gia_dinh_phan_doi'
OPTIONAL MATCH (hv_ct:HanhVi:{TOPIC_LABEL} {{id: 'can_tro_ket_hon', topic: '{TOPIC}'}})
WHERE yt = 'khac_tin_nguong_gia_dinh_phan_doi'

OPTIONAL MATCH (tthn_ly:TinhTrangHonNhan:{TOPIC_LABEL} {{
  id: 'hon_nhan_truoc_da_cham_dut', topic: '{TOPIC}'
}})
WHERE yt = 'ho_khau_sau_ly_hon' AND tthn = 'da_ly_hon'
OPTIONAL MATCH (tthn_co:TinhTrangHonNhan:{TOPIC_LABEL} {{
  id: 'dang_co_vo_hoac_chong', topic: '{TOPIC}'
}})
WHERE yt = 'ho_khau_sau_ly_hon' AND tthn = 'dang_co_vo_chong'

OPTIONAL MATCH (dk_nam:DieuKien:{TOPIC_LABEL} {{id: 'nam_tu_du_20_tuoi', topic: '{TOPIC}'}})
WHERE seed_tuoi = true
OPTIONAL MATCH (dk_nu:DieuKien:{TOPIC_LABEL} {{id: 'nu_tu_du_18_tuoi', topic: '{TOPIC}'}})
WHERE seed_tuoi = true

OPTIONAL MATCH (dk:DieuKien:{TOPIC_LABEL} {{id: 'du_dieu_kien_ket_hon', topic: '{TOPIC}'}})
WHERE seed_dk = true

WITH wl, kc, yt,
  [x IN collect(DISTINCT qd) + collect(DISTINCT dk_tn) + collect(DISTINCT qd_gd)
       + collect(DISTINCT hv_ct) + collect(DISTINCT tthn_ly) + collect(DISTINCT tthn_co)
       + collect(DISTINCT dk_nam) + collect(DISTINCT dk_nu) + collect(DISTINCT dk)
   WHERE x IS NOT NULL] AS seed_nodes,
  CASE yt
    WHEN 'khac_tin_nguong_gia_dinh_phan_doi' THEN
      [x IN collect(DISTINCT qd) + collect(DISTINCT dk_tn) + collect(DISTINCT qd_gd)
           + collect(DISTINCT hv_ct)
       WHERE x IS NOT NULL]
    WHEN 'ho_khau_sau_ly_hon' THEN
      [x IN collect(DISTINCT qd) + collect(DISTINCT tthn_ly) + collect(DISTINCT tthn_co)
       WHERE x IS NOT NULL]
    WHEN 'quan_he_giao_vien_hoc_sinh' THEN
      [x IN collect(DISTINCT qd) + collect(DISTINCT dk_nam) + collect(DISTINCT dk_nu)
           + collect(DISTINCT dk_tn)
       WHERE x IS NOT NULL]
    WHEN 'xung_khac_tuoi' THEN
      [x IN collect(DISTINCT qd) + collect(DISTINCT dk) WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT qd) WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: YeuToXaHoiKhongPhaiTroNgaiParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    yt = params.yeu_to_xa_hoi
    qd_id = _YEU_TO_QD.get(yt, "")
    seed_tuoi = yt == "quan_he_giao_vien_hoc_sinh" or params.co_du_tuoi_ro_rang == "co"
    seed_dk = yt == "xung_khac_tuoi" or params.khia_canh_yeu_to_xa_hoi in (
        "co_duoc_ket_hon",
        "tong_quat",
    )
    return {
        "yt": yt,
        "qd_id": qd_id,
        "tthn": params.tinh_trang_hon_nhan_hien_tai,
        "kc": params.khia_canh_yeu_to_xa_hoi,
        "seed_tuoi": seed_tuoi,
        "seed_dk": seed_dk,
        "whitelist_dieu_ids": _DIEU_WHITELIST if use_wl else [],
    }


yeu_to_xa_hoi_khong_phai_tro_ngai = CypherTemplate(
    name="yeu_to_xa_hoi_khong_phai_tro_ngai",
    description=(
        "Xử lý các yếu tố đời sống không tự là điều kiện nội dung của Điều 8: khác "
        "tín ngưỡng/gia đình phản đối, hộ khẩu còn ở nhà chồng cũ, quan hệ giáo viên-học "
        "sinh và quan niệm xung khắc tuổi. Template kiểm tra yếu tố pháp lý thực sự "
        "liên quan thay vì trả lời được tuyệt đối. "
        "Ví dụ: Khác tín ngưỡng và ông bà phản đối có được kết hôn không?; "
        "Xung khắc tuổi có phải trở ngại kết hôn không?"
    ),
    params_schema=YeuToXaHoiKhongPhaiTroNgaiParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
