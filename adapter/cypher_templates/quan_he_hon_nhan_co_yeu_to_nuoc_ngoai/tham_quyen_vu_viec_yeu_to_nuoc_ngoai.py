"""Template — thẩm quyền giải quyết vụ việc có yếu tố nước ngoài (Đ123)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.quan_he_hon_nhan_co_yeu_to_nuoc_ngoai._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("loai_vu_viec",)
_DIEU_WHITELIST = ["Luat_HNGD_2014_Dieu_123"]


class ThamQuyenVuViecParams(BaseModel):
    loai_vu_viec: Literal[
        "dang_ky_ho_tich",
        "vu_viec_tai_toa_an",
        "ly_hon_tranh_chap_khu_vuc_bien_gioi",
        "khong_ro",
    ] = Field(description="đăng ký hộ tịch / Tòa án / biên giới → map tương ứng.")
    dia_ban: Literal["khu_vuc_bien_gioi", "ngoai_khu_vuc_bien_gioi", "khong_ro"] = Field(
        description="khu vực biên giới → khu_vuc_bien_gioi."
    )
    chu_the_doi_ung: Literal[
        "cong_dan_nuoc_lang_gieng", "nguoi_nuoc_ngoai_khac", "khong_ro"
    ] = Field(description="công dân nước láng giềng → cong_dan_nuoc_lang_gieng.")
    khia_canh_tham_quyen: Literal["co_quan", "cap_toa_an", "can_cu", "tong_quat"] = Field(
        description="cấp huyện nơi cư trú → cap_toa_an."
    )


_SEED_BODY = f"""
WITH $loai_vu_viec AS lv, $dia_ban AS db, $chu_the_doi_ung AS ct, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (l_ht_cq:CoQuan:{TOPIC_LABEL} {{id: 'co_quan_dang_ky_ho_tich', topic: '{TOPIC}'}})
WHERE lv = 'dang_ky_ho_tich'
OPTIONAL MATCH (l_ht_hv:HanhVi:{TOPIC_LABEL} {{
  id: 'dang_ky_ho_tich_theo_phap_luat_ho_tich', topic: '{TOPIC}'
}})
WHERE lv = 'dang_ky_ho_tich'

OPTIONAL MATCH (l_ta_cq:CoQuan:{TOPIC_LABEL} {{id: 'toa_an_co_tham_quyen', topic: '{TOPIC}'}})
WHERE lv = 'vu_viec_tai_toa_an'
OPTIONAL MATCH (l_ta_qd:QuyDinh:{TOPIC_LABEL} {{
  id: 'giai_quyet_tai_toa_an_theo_bo_luat_to_tung_dan_su', topic: '{TOPIC}'
}})
WHERE lv = 'vu_viec_tai_toa_an'

OPTIONAL MATCH (l_bg_qd:QuyDinh:{TOPIC_LABEL} {{
  id: 'cap_huyen_giai_quyet_vu_viec_bien_gioi', topic: '{TOPIC}'
}})
WHERE lv = 'ly_hon_tranh_chap_khu_vuc_bien_gioi'
  AND db IN ['khu_vuc_bien_gioi', 'khong_ro']
OPTIONAL MATCH (l_bg_qh:QuanHe:{TOPIC_LABEL} {{
  id: 'vu_viec_hon_nhan_gia_dinh_khu_vuc_bien_gioi', topic: '{TOPIC}'
}})
WHERE lv = 'ly_hon_tranh_chap_khu_vuc_bien_gioi'
  AND db IN ['khu_vuc_bien_gioi', 'khong_ro']
OPTIONAL MATCH (l_bg_ct:ChuThe:{TOPIC_LABEL} {{
  id: 'cong_dan_nuoc_lang_gieng_cung_cu_tru_khu_vuc_bien_gioi', topic: '{TOPIC}'
}})
WHERE lv = 'ly_hon_tranh_chap_khu_vuc_bien_gioi'
  AND ct IN ['cong_dan_nuoc_lang_gieng', 'khong_ro']

OPTIONAL MATCH (l_tq:QuyDinh:{TOPIC_LABEL} {{
  id: 'tham_quyen_giai_quyet_vu_viec_co_yeu_to_nuoc_ngoai', topic: '{TOPIC}'
}})
WHERE lv IN ['khong_ro', 'tong_quat']

WITH wl, lv,
  collect(DISTINCT l_ht_cq) + collect(DISTINCT l_ht_hv)
    + collect(DISTINCT l_ta_cq) + collect(DISTINCT l_ta_qd)
    + collect(DISTINCT l_bg_qd) + collect(DISTINCT l_bg_qh) + collect(DISTINCT l_bg_ct)
    + collect(DISTINCT l_tq) AS seed_nodes,
  CASE
    WHEN lv = 'dang_ky_ho_tich' THEN
      [x IN collect(DISTINCT l_ht_cq) + collect(DISTINCT l_ht_hv) WHERE x IS NOT NULL]
    WHEN lv = 'vu_viec_tai_toa_an' THEN
      [x IN collect(DISTINCT l_ta_cq) + collect(DISTINCT l_ta_qd) WHERE x IS NOT NULL]
    WHEN lv = 'ly_hon_tranh_chap_khu_vuc_bien_gioi' THEN
      [x IN collect(DISTINCT l_bg_qd) + collect(DISTINCT l_bg_qh) + collect(DISTINCT l_bg_ct)
       WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT l_tq) WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: ThamQuyenVuViecParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "loai_vu_viec": params.loai_vu_viec,
        "dia_ban": params.dia_ban,
        "chu_the_doi_ung": params.chu_the_doi_ung,
        "whitelist_dieu_ids": _DIEU_WHITELIST if use_wl else [],
    }


tham_quyen_vu_viec_yeu_to_nuoc_ngoai = CypherTemplate(
    name="tham_quyen_vu_viec_yeu_to_nuoc_ngoai",
    description=(
        "Dùng cho thẩm quyền chung tại Điều 123: đăng ký hộ tịch, vụ việc tại Tòa án "
        "và ngoại lệ cấp huyện ở khu vực biên giới. Không nhận câu thẩm quyền đã có "
        "nghiệp vụ đặc thù như ly hôn, xác định cha mẹ con, cấp dưỡng hay công nhận bản án. "
        "Ví dụ: Đăng ký hộ tịch vụ việc có yếu tố nước ngoài do cơ quan nào?; "
        "Tòa án cấp huyện tại khu vực biên giới giải quyết những vụ việc gì?"
    ),
    params_schema=ThamQuyenVuViecParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
