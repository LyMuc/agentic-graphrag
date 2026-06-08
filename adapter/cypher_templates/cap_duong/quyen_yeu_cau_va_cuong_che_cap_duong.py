"""Template — quyền yêu cầu và cưỡng chế thực hiện cấp dưỡng (Đ107 K2, Đ119)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.cap_duong._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("khia_canh",)
_DIEU_119_WHITELIST = ["Luat_HNGD_2014_Dieu_119"]

_NGUOI_YEU_CAU_TO_QUYEN = {
    "nguoi_duoc_cap_duong": "quyen_yeu_cau_cua_nguoi_duoc_cap_duong",
    "cha_me": "quyen_yeu_cau_cua_cha_me_nguoi_giam_ho",
    "nguoi_giam_ho": "quyen_yeu_cau_cua_cha_me_nguoi_giam_ho",
    "nguoi_than_thich": "quyen_yeu_cau_cua_nguoi_than_thich",
    "co_quan_quan_ly_gia_dinh": "quyen_yeu_cau_cua_co_quan_quan_ly_gia_dinh",
    "co_quan_quan_ly_tre_em": "quyen_yeu_cau_cua_co_quan_quan_ly_tre_em",
    "hoi_lien_hiep_phu_nu": "quyen_yeu_cau_cua_hoi_lien_hiep_phu_nu",
    "ca_nhan_co_quan_to_chuc_khac": "quyen_de_nghi_khi_phat_hien_tron_tranh",
}


class QuyenYeuCauVaCuongCheCapDuongParams(BaseModel):
    khia_canh: Literal[
        "chu_the_co_quyen_yeu_cau",
        "khoi_kien_buoc_thuc_hien",
        "tron_tranh",
        "tong_quat",
    ] = Field(
        description=(
            "Khía cạnh quyền yêu cầu/cưỡng chế. Map: ai có quyền yêu cầu "
            "→ chu_the_co_quyen_yeu_cau; khởi kiện/buộc trả/Tòa án "
            "→ khoi_kien_buoc_thuc_hien; trốn tránh/không chịu/chậm "
            "→ tron_tranh."
        )
    )
    nguoi_yeu_cau: Literal[
        "nguoi_duoc_cap_duong",
        "cha_me",
        "nguoi_giam_ho",
        "nguoi_than_thich",
        "co_quan_quan_ly_gia_dinh",
        "co_quan_quan_ly_tre_em",
        "hoi_lien_hiep_phu_nu",
        "ca_nhan_co_quan_to_chuc_khac",
        "khong_ro",
    ] = Field(description="Chủ thể yêu cầu Tòa án hoặc đề nghị cơ quan.")
    tinh_trang_thuc_hien: Literal[
        "khong_tu_nguyen",
        "tron_tranh",
        "cham_thuc_hien",
        "khong_ro",
    ] = Field(description="Tình trạng thực hiện nghĩa vụ của người cấp dưỡng.")
    doi_tuong_duoc_cap_duong: Literal[
        "con",
        "vo_chong_cu",
        "cha_me",
        "ong_ba_chau",
        "khac",
        "khong_ro",
    ] = Field(description="Người được cấp dưỡng (bổ sung node quan hệ).")


_SEED_BODY = f"""
WITH $khia_canh AS kc, $quyen_id AS qid, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (q:Quyen:{TOPIC_LABEL} {{id: qid, topic: '{TOPIC}'}})
WHERE kc = 'chu_the_co_quyen_yeu_cau' AND qid <> ''

OPTIONAL MATCH (q_all:Quyen:{TOPIC_LABEL})
WHERE kc IN ['chu_the_co_quyen_yeu_cau', 'tong_quat']
  AND (qid = '' OR q IS NULL)
  AND q_all.topic = '{TOPIC}'

OPTIONAL MATCH (hv_yc:HanhVi:{TOPIC_LABEL} {{id: 'yeu_cau_toa_an_buoc_thuc_hien_cap_duong', topic: '{TOPIC}'}})
WHERE kc IN ['khoi_kien_buoc_thuc_hien', 'tong_quat']
OPTIONAL MATCH (hq:HauQua:{TOPIC_LABEL} {{id: 'toa_an_buoc_thuc_hien_nghia_vu', topic: '{TOPIC}'}})
WHERE hv_yc IS NOT NULL

OPTIONAL MATCH (hv_tt:HanhVi:{TOPIC_LABEL} {{id: 'tron_tranh_nghia_vu_nuoi_duong', topic: '{TOPIC}'}})
WHERE kc IN ['tron_tranh', 'tong_quat']
OPTIONAL MATCH (hv_dn:HanhVi:{TOPIC_LABEL} {{id: 'de_nghi_co_quan_to_chuc_yeu_cau_toa_an', topic: '{TOPIC}'}})
WHERE kc = 'tron_tranh'

WITH wl, kc,
  [x IN collect(DISTINCT q) + collect(DISTINCT q_all)
       + collect(DISTINCT hv_yc) + collect(DISTINCT hq)
       + collect(DISTINCT hv_tt) + collect(DISTINCT hv_dn)
   WHERE x IS NOT NULL] AS seed_nodes,
  CASE kc
    WHEN 'chu_the_co_quyen_yeu_cau' THEN
      [x IN collect(DISTINCT q) + collect(DISTINCT q_all) WHERE x IS NOT NULL]
    WHEN 'khoi_kien_buoc_thuc_hien' THEN
      [x IN collect(DISTINCT hv_yc) + collect(DISTINCT hq) WHERE x IS NOT NULL]
    WHEN 'tron_tranh' THEN
      [x IN collect(DISTINCT hv_tt) + collect(DISTINCT hv_yc) + collect(DISTINCT hq)
           + collect(DISTINCT hv_dn)
       WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT q_all) + collect(DISTINCT hv_yc) + collect(DISTINCT hq)
       WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: QuyenYeuCauVaCuongCheCapDuongParams) -> dict[str, Any]:
    qid = _NGUOI_YEU_CAU_TO_QUYEN.get(params.nguoi_yeu_cau, "")
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "khia_canh": params.khia_canh,
        "quyen_id": qid,
        "whitelist_dieu_ids": _DIEU_119_WHITELIST if use_wl else [],
    }


quyen_yeu_cau_va_cuong_che_cap_duong = CypherTemplate(
    name="quyen_yeu_cau_va_cuong_che_cap_duong",
    description=(
        "Ai có quyền yêu cầu Tòa án buộc thực hiện nghĩa vụ cấp dưỡng và hậu quả khi "
        "trốn tránh hoặc không tự nguyện thực hiện (Đ107 khoản 2, Đ119). "
        "Ví dụ: đối tượng nào có quyền yêu cầu Tòa án; "
        "cha không thực hiện nghĩa vụ mẹ có quyền khởi kiện không; "
        "trốn tránh nghĩa vụ cấp dưỡng và biện pháp buộc thực hiện."
    ),
    params_schema=QuyenYeuCauVaCuongCheCapDuongParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
