"""Template — thay đổi người trực tiếp nuôi con sau ly hôn (Đ84)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.cha_me_con_sau_ly_hon._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("can_cu_thay_doi",)
_TONG_QUAT_WHITELIST = [
    "Luat_HNGD_2014_Dieu_84",
    "Luat_HNGD_2014_Dieu_84_Khoan_1",
    "Luat_HNGD_2014_Dieu_84_Khoan_2",
]

_NGUOI_YEU_CAU_TO_CT = {
    "cha": "cha_me_sau_ly_hon",
    "me": "cha_me_sau_ly_hon",
    "nguoi_than_thich": "nguoi_than_thich_yeu_cau_thay_doi_nguoi_nuoi",
    "co_quan_quan_ly_gia_dinh": "co_quan_quan_ly_gia_dinh_yeu_cau_thay_doi_nguoi_nuoi",
    "co_quan_quan_ly_tre_em": "co_quan_quan_ly_tre_em_yeu_cau_thay_doi_nguoi_nuoi",
    "hoi_lien_hiep_phu_nu": "hoi_lien_hiep_phu_nu_yeu_cau_thay_doi_nguoi_nuoi",
}


class ThayDoiNguoiTrucTiepNuoiConParams(BaseModel):
    can_cu_thay_doi: Literal[
        "thoa_thuan_cua_cha_me",
        "nguoi_nuoi_khong_con_du_dieu_kien",
        "ca_cha_me_khong_du_dieu_kien",
        "tong_quat",
        "khong_ro",
    ] = Field(
        description=(
            "Căn cứ thay đổi. Map: hai bên đồng ý → thoa_thuan_cua_cha_me; "
            "người đang nuôi chết/đi tù/đi xa/bỏ mặc → nguoi_nuoi_khong_con_du_dieu_kien; "
            "cả cha mẹ không nuôi được → ca_cha_me_khong_du_dieu_kien; hỏi liệt kê → tong_quat."
        )
    )
    nguoi_yeu_cau: Literal[
        "cha",
        "me",
        "nguoi_than_thich",
        "co_quan_quan_ly_gia_dinh",
        "co_quan_quan_ly_tre_em",
        "hoi_lien_hiep_phu_nu",
        "khong_ro",
    ] = Field(description="Chủ thể yêu cầu thay đổi người nuôi.")
    do_tuoi_con: Literal[
        "duoi_36_thang",
        "tu_36_thang_den_duoi_7_tuoi",
        "tu_du_7_tuoi",
        "khong_ro",
    ] = Field(description="Độ tuổi con.")
    tinh_trang_nguoi_dang_nuoi: Literal[
        "chet",
        "di_xa_khong_truc_tiep_cham_soc",
        "di_tu",
        "that_nghiep_kho_khan",
        "cham_soc_khong_tot",
        "van_du_dieu_kien",
        "khong_ro",
    ] = Field(
        description=(
            "Tình trạng người đang nuôi — chỉ là dữ kiện, không kết luận tự động."
        )
    )
    ket_qua_de_nghi: Literal[
        "giao_cho_cha",
        "giao_cho_me",
        "giao_cho_nguoi_than",
        "giao_cho_nguoi_giam_ho",
        "khong_ro",
    ] = Field(description="Người được đề nghị nhận nuôi.")


_SEED_BODY = f"""
WITH $can_cu_thay_doi AS cc, $nguoi_yeu_cau AS ny, $do_tuoi_con AS dt,
     $ct_yeu_cau_id AS ct_id, $whitelist_dieu_ids AS wl

MATCH (q:Quyen:{TOPIC_LABEL} {{id: 'quyen_yeu_cau_thay_doi_nguoi_truc_tiep_nuoi_con', topic: '{TOPIC}'}})
MATCH (q)-[:THUC_HIEN]->(hv:HanhVi:{TOPIC_LABEL} {{
  id: 'yeu_cau_toa_an_thay_doi_nguoi_truc_tiep_nuoi_con', topic: '{TOPIC}'
}})

OPTIONAL MATCH (ct:ChuThe:{TOPIC_LABEL} {{id: ct_id, topic: '{TOPIC}'}})
WHERE ny <> 'khong_ro' AND ct_id <> ''
OPTIONAL MATCH (ct)-[:CO_QUYEN]->(q)

OPTIONAL MATCH (hv)-[:AP_DUNG_KHI]->(dk_tt:DieuKien:{TOPIC_LABEL} {{
  id: 'cha_me_thoa_thuan_thay_doi_nguoi_nuoi_phu_hop_loi_ich_con', topic: '{TOPIC}'
}})
WHERE cc = 'thoa_thuan_cua_cha_me'
OPTIONAL MATCH (tt:ThoaThuan:{TOPIC_LABEL} {{id: 'thoa_thuan_thay_doi_nguoi_truc_tiep_nuoi_con', topic: '{TOPIC}'}})
WHERE cc = 'thoa_thuan_cua_cha_me'

OPTIONAL MATCH (hv)-[:AP_DUNG_KHI]->(dk_b:DieuKien:{TOPIC_LABEL} {{
  id: 'nguoi_truc_tiep_nuoi_khong_con_du_dieu_kien', topic: '{TOPIC}'
}})
WHERE cc IN ['nguoi_nuoi_khong_con_du_dieu_kien', 'khong_ro', 'tong_quat']
OPTIONAL MATCH (hv)-[:AP_DUNG_KHI]->(dk5:DieuKien:{TOPIC_LABEL} {{
  id: 'can_cu_diem_b_khoan_2_va_loi_ich_cua_con', topic: '{TOPIC}'
}})
WHERE cc = 'nguoi_nuoi_khong_con_du_dieu_kien'
  AND ny IN ['nguoi_than_thich', 'co_quan_quan_ly_gia_dinh',
             'co_quan_quan_ly_tre_em', 'hoi_lien_hiep_phu_nu']

OPTIONAL MATCH (hv)-[:AP_DUNG_KHI]->(dk7:DieuKien:{TOPIC_LABEL} {{
  id: 'thay_doi_nguoi_nuoi_phai_xem_xet_nguyen_vong_con_tu_du_bay_tuoi', topic: '{TOPIC}'
}})
WHERE dt = 'tu_du_7_tuoi'

OPTIONAL MATCH (dk_ca:DieuKien:{TOPIC_LABEL} {{
  id: 'ca_cha_va_me_deu_khong_du_dieu_kien_nuoi_con', topic: '{TOPIC}'
}})
WHERE cc = 'ca_cha_me_khong_du_dieu_kien'
OPTIONAL MATCH (dk_ca)-[:DAN_TOI]->(hq_gh:HauQua:{TOPIC_LABEL} {{
  id: 'toa_an_giao_con_cho_nguoi_giam_ho', topic: '{TOPIC}'
}})
WHERE cc = 'ca_cha_me_khong_du_dieu_kien'

OPTIONAL MATCH (hv_xem:HanhVi:{TOPIC_LABEL} {{
  id: 'toa_an_xem_xet_thay_doi_nguoi_truc_tiep_nuoi_con', topic: '{TOPIC}'
}})
WHERE cc IN ['tong_quat', 'khong_ro']
OPTIONAL MATCH (hv_xem)-[:DAN_TOI]->(hq:HauQua:{TOPIC_LABEL} {{
  id: 'toa_an_thay_doi_nguoi_truc_tiep_nuoi_con', topic: '{TOPIC}'
}})
WHERE cc IN ['tong_quat', 'khong_ro']

WITH wl, cc,
  collect(DISTINCT q) + collect(DISTINCT hv) + collect(DISTINCT ct)
    + collect(DISTINCT dk_tt) + collect(DISTINCT tt)
    + collect(DISTINCT dk_b) + collect(DISTINCT dk5) + collect(DISTINCT dk7)
    + collect(DISTINCT dk_ca) + collect(DISTINCT hq_gh)
    + collect(DISTINCT hv_xem) + collect(DISTINCT hq) AS seed_nodes,
  CASE cc
    WHEN 'thoa_thuan_cua_cha_me' THEN
      [x IN collect(DISTINCT dk_tt) + collect(DISTINCT tt) WHERE x IS NOT NULL]
    WHEN 'nguoi_nuoi_khong_con_du_dieu_kien' THEN
      [x IN collect(DISTINCT dk_b) + collect(DISTINCT dk5) + collect(DISTINCT dk7)
       WHERE x IS NOT NULL]
    WHEN 'ca_cha_me_khong_du_dieu_kien' THEN
      [x IN collect(DISTINCT dk_ca) + collect(DISTINCT hq_gh) WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT hv) + collect(DISTINCT dk_b) + collect(DISTINCT dk7)
           + collect(DISTINCT hv_xem) + collect(DISTINCT hq)
       WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: ThayDoiNguoiTrucTiepNuoiConParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    ct_id = _NGUOI_YEU_CAU_TO_CT.get(params.nguoi_yeu_cau, "")
    if params.can_cu_thay_doi == "nguoi_nuoi_khong_con_du_dieu_kien" and not ct_id:
        if params.nguoi_yeu_cau in ("cha", "me"):
            ct_id = "cha_me_sau_ly_hon"
    return {
        "can_cu_thay_doi": params.can_cu_thay_doi,
        "nguoi_yeu_cau": params.nguoi_yeu_cau,
        "do_tuoi_con": params.do_tuoi_con,
        "ct_yeu_cau_id": ct_id,
        "whitelist_dieu_ids": _TONG_QUAT_WHITELIST if use_wl else [],
    }


thay_doi_nguoi_truc_tiep_nuoi_con = CypherTemplate(
    name="thay_doi_nguoi_truc_tiep_nuoi_con",
    description=(
        "Thay đổi người trực tiếp nuôi sau khi đã có quyết định: chủ thể yêu cầu, "
        "căn cứ khoản 2, nguyện vọng con từ 07 tuổi, giao cho người giám hộ. "
        "Ví dụ: giành lại quyền nuôi khi mẹ đi xuất khẩu lao động; thay đổi vì con "
        "thiếu thốn với mẹ; tuổi phải xem xét nguyện vọng; thay đổi khi chồng đang nuôi con đã mất."
    ),
    params_schema=ThayDoiNguoiTrucTiepNuoiConParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
