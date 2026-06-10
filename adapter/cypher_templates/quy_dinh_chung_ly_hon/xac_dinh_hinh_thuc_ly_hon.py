"""Template — xác định hình thức ly hôn (Đ51, 55, 56)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.quy_dinh_chung_ly_hon._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("khia_canh_hinh_thuc",)
_DIEU_51_55_56_WHITELIST = [
    "Luat_HNGD_2014_Dieu_51",
    "Luat_HNGD_2014_Dieu_55",
    "Luat_HNGD_2014_Dieu_56",
]


class XacDinhHinhThucLyHonParams(BaseModel):
    y_chi_vo_chong: Literal[
        "ca_hai_dong_y", "mot_ben_khong_dong_y", "chua_ro"
    ] = Field(
        description="Hai bên đồng ý → ca_hai_dong_y; một bên không chịu → mot_ben_khong_dong_y."
    )
    khia_canh_hinh_thuc: Literal[
        "so_sanh_thuan_tinh_don_phuong",
        "dieu_kien_tien_hanh",
        "chu_the_dung_ten_yeu_cau",
        "tong_quat",
    ] = Field(
        description=(
            "So sánh hai hình thức → so_sanh_thuan_tinh_don_phuong; "
            "điều kiện tiến hành → dieu_kien_tien_hanh; ai đứng tên đơn "
            "→ chu_the_dung_ten_yeu_cau."
        )
    )
    co_con_duoi_12_thang: Literal["co", "khong", "khong_ro"] = Field(
        description="Con dưới 12 tháng → co."
    )
    co_tranh_chap_tai_san_con: Literal["co", "khong", "khong_ro"] = Field(
        description="Có tranh chấp tài sản/con → co."
    )
    boi_canh_to_tung: Literal["khac_dia_phuong", "luat_su_soan_don", "khong_ro"] = Field(
        description="Luật sư soạn đơn → luat_su_soan_don."
    )


_SEED_BODY = f"""
WITH $yc AS yc, $kc AS kc, $con_nho AS cn, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (qv:Quyen:{TOPIC_LABEL} {{id: 'quyen_vo_yeu_cau_ly_hon', topic: '{TOPIC}'}})
OPTIONAL MATCH (qc:Quyen:{TOPIC_LABEL} {{id: 'quyen_chong_yeu_cau_ly_hon', topic: '{TOPIC}'}})
OPTIONAL MATCH (qca:Quyen:{TOPIC_LABEL} {{id: 'quyen_ca_hai_vo_chong_yeu_cau_ly_hon', topic: '{TOPIC}'}})

OPTIONAL MATCH (ht_tt:HinhThucLyHon:{TOPIC_LABEL} {{id: 'thuan_tinh_ly_hon', topic: '{TOPIC}'}})
WHERE yc IN ['ca_hai_dong_y', 'chua_ro'] OR kc IN ['so_sanh_thuan_tinh_don_phuong', 'dieu_kien_tien_hanh', 'tong_quat']
OPTIONAL MATCH (dk_tt:DieuKien:{TOPIC_LABEL} {{id: 'hai_ben_that_su_tu_nguyen_ly_hon', topic: '{TOPIC}'}})
WHERE ht_tt IS NOT NULL

OPTIONAL MATCH (ht_dp:HinhThucLyHon:{TOPIC_LABEL} {{id: 'ly_hon_theo_yeu_cau_mot_ben', topic: '{TOPIC}'}})
WHERE yc IN ['mot_ben_khong_dong_y', 'chua_ro'] OR kc IN ['so_sanh_thuan_tinh_don_phuong', 'dieu_kien_tien_hanh', 'tong_quat']
OPTIONAL MATCH (hv_dp:HanhVi:{TOPIC_LABEL} {{id: 'mot_ben_yeu_cau_ly_hon', topic: '{TOPIC}'}})
WHERE ht_dp IS NOT NULL

OPTIONAL MATCH (hc:Quyen:{TOPIC_LABEL} {{id: 'han_che_quyen_chong_yeu_cau_ly_hon', topic: '{TOPIC}'}})
WHERE cn = 'co'
OPTIONAL MATCH (dk_cn:DieuKien:{TOPIC_LABEL} {{id: 'vo_dang_nuoi_con_duoi_12_thang', topic: '{TOPIC}'}})
WHERE hc IS NOT NULL

OPTIONAL MATCH (gd_tl:GiaiDoanLyHon:{TOPIC_LABEL} {{id: 'thu_ly_don_yeu_cau_ly_hon', topic: '{TOPIC}'}})
WHERE kc = 'dieu_kien_tien_hanh'

WITH wl, kc, yc,
  [x IN collect(DISTINCT qv) + collect(DISTINCT qc) + collect(DISTINCT qca)
       + collect(DISTINCT ht_tt) + collect(DISTINCT dk_tt)
       + collect(DISTINCT ht_dp) + collect(DISTINCT hv_dp)
       + collect(DISTINCT hc) + collect(DISTINCT dk_cn)
       + collect(DISTINCT gd_tl)
   WHERE x IS NOT NULL] AS seed_nodes,
  CASE kc
    WHEN 'chu_the_dung_ten_yeu_cau' THEN
      [x IN collect(DISTINCT qv) + collect(DISTINCT qc) + collect(DISTINCT qca)
       WHERE x IS NOT NULL]
    WHEN 'dieu_kien_tien_hanh' THEN
      [x IN collect(DISTINCT ht_tt) + collect(DISTINCT ht_dp) + collect(DISTINCT gd_tl)
       WHERE x IS NOT NULL]
    WHEN 'so_sanh_thuan_tinh_don_phuong' THEN
      CASE yc
        WHEN 'ca_hai_dong_y' THEN [x IN collect(DISTINCT ht_tt) + collect(DISTINCT dk_tt) WHERE x IS NOT NULL]
        WHEN 'mot_ben_khong_dong_y' THEN [x IN collect(DISTINCT ht_dp) + collect(DISTINCT hv_dp) WHERE x IS NOT NULL]
        ELSE [x IN collect(DISTINCT ht_tt) + collect(DISTINCT ht_dp) WHERE x IS NOT NULL]
      END
    ELSE
      [x IN collect(DISTINCT ht_tt) + collect(DISTINCT ht_dp) WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: XacDinhHinhThucLyHonParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "yc": params.y_chi_vo_chong,
        "kc": params.khia_canh_hinh_thuc,
        "con_nho": params.co_con_duoi_12_thang,
        "whitelist_dieu_ids": _DIEU_51_55_56_WHITELIST if use_wl else [],
    }


xac_dinh_hinh_thuc_ly_hon = CypherTemplate(
    name="xac_dinh_hinh_thuc_ly_hon",
    description=(
        "So sánh thuận tình và ly hôn theo yêu cầu một bên, xác định ai đứng tên "
        "yêu cầu hoặc điều kiện tiến hành ly hôn nói chung (Đ51, 55, 56). "
        "Ví dụ: Chồng không đồng ý thì có thể đơn phương không; "
        "Câu hỏi cả thuận tình và đơn phương trong cùng tình huống; "
        "Luật sư để người vợ đứng tên đơn có bất lợi không."
    ),
    params_schema=XacDinhHinhThucLyHonParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
