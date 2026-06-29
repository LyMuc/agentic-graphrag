"""Template — mức và phân bổ cấp dưỡng (Đ108-109, Đ116)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from server.infrastructure.neo4j.cypher_templates import CypherTemplate
from server.infrastructure.neo4j.cypher_templates.cap_duong._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("khia_canh_muc",)
_DIEU_116_WHITELIST = ["Luat_HNGD_2014_Dieu_116"]
_DIEU_82_K2 = "Luat_HNGD_2014_Dieu_82_Khoan_2"


class MucVaPhanBoCapDuongParams(BaseModel):
    khia_canh_muc: Literal[
        "xac_dinh_muc",
        "muc_toi_thieu",
        "thay_doi_muc",
        "mot_nguoi_nhieu_nguoi",
        "nhieu_nguoi_cung_cap_duong",
        "tong_quat",
    ] = Field(
        description=(
            "Khía cạnh mức cấp dưỡng. Map: bao nhiêu/mức thế nào → xac_dinh_muc; "
            "tối thiểu/ít nhất → muc_toi_thieu; giảm/tăng/thay đổi mức → thay_doi_muc; "
            "một người cấp dưỡng nhiều người → mot_nguoi_nhieu_nguoi; "
            "nhiều người cùng góp → nhieu_nguoi_cung_cap_duong."
        )
    )
    doi_tuong_nhan: Literal[
        "con",
        "vo_chong_cu",
        "cha_me",
        "ong_ba_chau",
        "anh_chi_em",
        "khac",
        "khong_ro",
    ] = Field(description="Đối tượng được cấp dưỡng.")
    so_luong_ben: Literal[
        "mot_voi_mot",
        "mot_nguoi_cap_duong_nhieu_nguoi",
        "nhieu_nguoi_cung_cap_duong",
        "khong_ro",
    ] = Field(description="Số lượng bên trong quan hệ cấp dưỡng.")
    hoan_canh_kinh_te: Literal["co_kha_nang", "kho_khan", "khong_ro"] = Field(
        description="Hoàn cảnh kinh tế người có nghĩa vụ."
    )
    chu_ky_duoc_hoi: Literal["hang_thang", "khac", "khong_ro"] = Field(
        description="Chu kỳ cấp dưỡng được hỏi (mỗi tháng → hang_thang)."
    )


_SEED_BODY = f"""
WITH $khia_canh_muc AS km, $doi_tuong_nhan AS dtn, $so_luong_ben AS slb,
     $whitelist_dieu_ids AS wl, $them_dieu_82 AS them82

OPTIONAL MATCH (tt:ThoaThuan:{TOPIC_LABEL})
WHERE tt.id IN ['thoa_thuan_muc_cap_duong', 'thoa_thuan_thay_doi_muc_cap_duong']
  AND tt.topic = '{TOPIC}'
  AND km IN ['xac_dinh_muc', 'muc_toi_thieu', 'thay_doi_muc', 'tong_quat']

OPTIONAL MATCH (dk1:DieuKien:{TOPIC_LABEL} {{id: 'thu_nhap_kha_nang_thuc_te_nguoi_cap_duong', topic: '{TOPIC}'}})
OPTIONAL MATCH (dk2:DieuKien:{TOPIC_LABEL} {{id: 'nhu_cau_thiet_yeu_nguoi_duoc_cap_duong', topic: '{TOPIC}'}})
OPTIONAL MATCH (hq:HauQua:{TOPIC_LABEL} {{id: 'toa_an_quyet_dinh_muc_phuong_thuc', topic: '{TOPIC}'}})

OPTIONAL MATCH (nv108:NghiaVu:{TOPIC_LABEL} {{id: 'mot_nguoi_cap_duong_nhieu_nguoi', topic: '{TOPIC}'}})
WHERE km = 'mot_nguoi_nhieu_nguoi' OR slb = 'mot_nguoi_cap_duong_nhieu_nguoi'
OPTIONAL MATCH (tt108:ThoaThuan:{TOPIC_LABEL} {{id: 'thoa_thuan_muc_phuong_thuc_mot_nguoi_nhieu_nguoi', topic: '{TOPIC}'}})
WHERE nv108 IS NOT NULL

OPTIONAL MATCH (nv109:NghiaVu:{TOPIC_LABEL} {{id: 'nhieu_nguoi_cung_cap_duong', topic: '{TOPIC}'}})
WHERE km = 'nhieu_nguoi_cung_cap_duong' OR slb = 'nhieu_nguoi_cung_cap_duong'
OPTIONAL MATCH (tt109:ThoaThuan:{TOPIC_LABEL} {{id: 'thoa_thuan_muc_dong_gop_nhieu_nguoi', topic: '{TOPIC}'}})
WHERE nv109 IS NOT NULL

OPTIONAL MATCH (nv82:NghiaVu:{TOPIC_LABEL} {{
  id: 'nghia_vu_cap_duong_cha_me_khong_truc_tiep_nuoi_con', topic: '{TOPIC}'
}})
WHERE them82 = true AND dtn = 'con'

WITH wl, km,
  [x IN collect(DISTINCT tt) + collect(DISTINCT dk1) + collect(DISTINCT dk2)
       + collect(DISTINCT hq) + collect(DISTINCT nv108) + collect(DISTINCT tt108)
       + collect(DISTINCT nv109) + collect(DISTINCT tt109) + collect(DISTINCT nv82)
   WHERE x IS NOT NULL] AS seed_nodes,
  CASE km
    WHEN 'thay_doi_muc' THEN
      [x IN collect(DISTINCT tt) WHERE x IS NOT NULL AND x.id = 'thoa_thuan_thay_doi_muc_cap_duong']
    WHEN 'mot_nguoi_nhieu_nguoi' THEN
      [x IN collect(DISTINCT nv108) + collect(DISTINCT tt108) WHERE x IS NOT NULL]
    WHEN 'nhieu_nguoi_cung_cap_duong' THEN
      [x IN collect(DISTINCT nv109) + collect(DISTINCT tt109) WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT tt) + collect(DISTINCT dk1) + collect(DISTINCT dk2)
           + collect(DISTINCT hq) + collect(DISTINCT nv82)
       WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: MucVaPhanBoCapDuongParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "khia_canh_muc": params.khia_canh_muc,
        "doi_tuong_nhan": params.doi_tuong_nhan,
        "so_luong_ben": params.so_luong_ben,
        "whitelist_dieu_ids": _DIEU_116_WHITELIST if use_wl else [],
        "them_dieu_82": params.doi_tuong_nhan == "con",
    }


muc_va_phan_bo_cap_duong = CypherTemplate(
    name="muc_va_phan_bo_cap_duong",
    description=(
        "Cách xác định mức cấp dưỡng, mức tối thiểu, thay đổi mức và phân bổ khi một "
        "người cấp dưỡng nhiều người hoặc nhiều người cùng cấp dưỡng (Đ108-109, Đ116). "
        "Ví dụ: mức cấp dưỡng nuôi con tối thiểu là bao nhiêu; "
        "không đồng ý mức cấp dưỡng 3 triệu đồng; tiền cấp dưỡng cho con sau ly hôn."
    ),
    params_schema=MucVaPhanBoCapDuongParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
