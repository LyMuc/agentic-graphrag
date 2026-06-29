"""Template — xác định người trực tiếp nuôi con khi ly hôn (Đ81 K2-3)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from server.infrastructure.neo4j.cypher_templates import CypherTemplate
from server.infrastructure.neo4j.cypher_templates.cha_me_con_sau_ly_hon._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("tinh_huong",)
_TONG_QUAT_WHITELIST = ["Luat_HNGD_2014_Dieu_81"]


class XacDinhNguoiTrucTiepNuoiConParams(BaseModel):
    tinh_huong: Literal[
        "cha_me_thoa_thuan",
        "khong_thoa_thuan_toa_quyet_dinh",
        "so_sanh_dieu_kien_cha_me",
        "cha_muon_truc_tiep_nuoi",
        "me_muon_truc_tiep_nuoi",
        "tong_quat",
    ] = Field(
        description=(
            "Tình huống. Map: hai bên thống nhất → cha_me_thoa_thuan; tranh chấp/giành "
            "quyền → khong_thoa_thuan_toa_quyet_dinh; so sánh nghề/thu nhập/hoàn cảnh "
            "→ so_sanh_dieu_kien_cha_me; bố/cha muốn nuôi → cha_muon_truc_tiep_nuoi; "
            "mẹ/vợ muốn nuôi → me_muon_truc_tiep_nuoi."
        )
    )
    do_tuoi_con: Literal[
        "duoi_36_thang",
        "tu_36_thang_den_duoi_7_tuoi",
        "tu_du_7_tuoi",
        "khong_ro",
    ] = Field(
        description=(
            "Độ tuổi con. Map: dưới 3 tuổi/36 tháng → duoi_36_thang; "
            "từ 36 tháng đến dưới 7 tuổi → tu_36_thang_den_duoi_7_tuoi; "
            "từ đủ 7 tuổi → tu_du_7_tuoi."
        )
    )
    yeu_to_trong_tam: Literal[
        "quyen_loi_moi_mat_cua_con",
        "nguyen_vong_cua_con",
        "dieu_kien_kinh_te",
        "dieu_kien_cham_soc",
        "tong_quat",
    ] = Field(
        description=(
            "Yếu tố trọng tâm. Map: lợi ích/quyền lợi con → quyen_loi_moi_mat_cua_con; "
            "con chọn/ý kiến/nguyện vọng → nguyen_vong_cua_con; thu nhập/nghề nghiệp "
            "→ dieu_kien_kinh_te; chăm con/điều kiện nuôi → dieu_kien_cham_soc."
        )
    )
    ben_de_nghi_nuoi: Literal["cha", "me", "ca_hai", "khong_ro"] = Field(
        description="Bên đề nghị trực tiếp nuôi: cha/mẹ/cả hai/không rõ."
    )


_SEED_BODY = f"""
WITH $tinh_huong AS th, $do_tuoi_con AS dt, $yeu_to_trong_tam AS yt,
     $whitelist_dieu_ids AS wl

OPTIONAL MATCH (tt:ThoaThuan:{TOPIC_LABEL} {{id: 'thoa_thuan_nguoi_truc_tiep_nuoi_con', topic: '{TOPIC}'}})
WHERE th IN ['cha_me_thoa_thuan', 'tong_quat']
OPTIONAL MATCH (tt)-[:DIEU_CHINH]->(hv_tt:HanhVi:{TOPIC_LABEL})
WHERE th IN ['cha_me_thoa_thuan', 'tong_quat']
OPTIONAL MATCH (hv_tt)-[:DAN_TOI]->(hq_tt:HauQua:{TOPIC_LABEL})
WHERE th IN ['cha_me_thoa_thuan', 'tong_quat']

OPTIONAL MATCH (hv_toa:HanhVi:{TOPIC_LABEL} {{id: 'toa_an_quyet_dinh_giao_con_cho_mot_ben', topic: '{TOPIC}'}})
WHERE th IN ['khong_thoa_thuan_toa_quyet_dinh', 'so_sanh_dieu_kien_cha_me',
             'cha_muon_truc_tiep_nuoi', 'me_muon_truc_tiep_nuoi', 'tong_quat']
OPTIONAL MATCH (hv_toa)-[:AP_DUNG_KHI]->(dk:DieuKien:{TOPIC_LABEL})
WHERE th IN ['khong_thoa_thuan_toa_quyet_dinh', 'so_sanh_dieu_kien_cha_me',
             'cha_muon_truc_tiep_nuoi', 'me_muon_truc_tiep_nuoi', 'tong_quat']
  AND (yt = 'quyen_loi_moi_mat_cua_con' AND dk.id = 'bao_dam_quyen_loi_moi_mat_cua_con'
       OR th = 'khong_thoa_thuan_toa_quyet_dinh' AND dk.id = 'cha_me_khong_thoa_thuan_duoc_nguoi_nuoi'
       OR yt = 'tong_quat' OR th = 'tong_quat')
OPTIONAL MATCH (hv_toa)-[:DAN_TOI]->(hq_toa:HauQua:{TOPIC_LABEL})
WHERE th IN ['khong_thoa_thuan_toa_quyet_dinh', 'so_sanh_dieu_kien_cha_me',
             'cha_muon_truc_tiep_nuoi', 'me_muon_truc_tiep_nuoi', 'tong_quat']

OPTIONAL MATCH (hv_nv:HanhVi:{TOPIC_LABEL} {{id: 'xem_xet_nguyen_vong_cua_con', topic: '{TOPIC}'}})
WHERE dt = 'tu_du_7_tuoi' OR yt = 'nguyen_vong_cua_con'
OPTIONAL MATCH (hv_nv)-[:AP_DUNG_KHI]->(dk7:DieuKien:{TOPIC_LABEL} {{id: 'con_tu_du_bay_tuoi', topic: '{TOPIC}'}})
WHERE dt = 'tu_du_7_tuoi' OR yt = 'nguyen_vong_cua_con'

OPTIONAL MATCH (dk36:DieuKien:{TOPIC_LABEL} {{id: 'con_duoi_ba_muoi_sau_thang_tuoi', topic: '{TOPIC}'}})
WHERE dt = 'duoi_36_thang'
OPTIONAL MATCH (hq36:HauQua:{TOPIC_LABEL} {{id: 'giao_con_duoi_ba_muoi_sau_thang_cho_me', topic: '{TOPIC}'}})
WHERE dt = 'duoi_36_thang'

WITH wl, th, dt, yt,
  collect(DISTINCT tt) + collect(DISTINCT hv_tt) + collect(DISTINCT hq_tt)
    + collect(DISTINCT hv_toa) + collect(DISTINCT dk) + collect(DISTINCT hq_toa)
    + collect(DISTINCT hv_nv) + collect(DISTINCT dk7)
    + collect(DISTINCT dk36) + collect(DISTINCT hq36) AS seed_nodes,
  CASE th
    WHEN 'cha_me_thoa_thuan' THEN
      [x IN collect(DISTINCT tt) + collect(DISTINCT hv_tt) + collect(DISTINCT hq_tt)
       WHERE x IS NOT NULL]
    WHEN 'khong_thoa_thuan_toa_quyet_dinh' THEN
      [x IN collect(DISTINCT hv_toa) + collect(DISTINCT dk) + collect(DISTINCT hq_toa)
           + collect(DISTINCT hv_nv) + collect(DISTINCT dk7)
       WHERE x IS NOT NULL]
    WHEN 'so_sanh_dieu_kien_cha_me' THEN
      [x IN collect(DISTINCT hv_toa) + collect(DISTINCT dk) + collect(DISTINCT hq_toa)
       WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT tt) + collect(DISTINCT hv_toa) + collect(DISTINCT dk)
           + collect(DISTINCT hq_toa) + collect(DISTINCT hv_nv) + collect(DISTINCT dk7)
           + collect(DISTINCT dk36) + collect(DISTINCT hq36)
       WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: XacDinhNguoiTrucTiepNuoiConParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "tinh_huong": params.tinh_huong,
        "do_tuoi_con": params.do_tuoi_con,
        "yeu_to_trong_tam": params.yeu_to_trong_tam,
        "whitelist_dieu_ids": _TONG_QUAT_WHITELIST if use_wl else [],
    }


xac_dinh_nguoi_truc_tiep_nuoi_con = CypherTemplate(
    name="xac_dinh_nguoi_truc_tiep_nuoi_con",
    description=(
        "Xác định người trực tiếp nuôi con tại thời điểm ly hôn: ưu tiên thỏa thuận; "
        "nếu không thỏa thuận Tòa án căn cứ quyền lợi về mọi mặt của con và xem xét "
        "nguyện vọng con từ đủ 07 tuổi. Ví dụ: điều kiện để vợ hoặc chồng giành quyền "
        "nuôi; so sánh chồng giám đốc và vợ nội trợ; tuổi con được lựa chọn sống với "
        "cha hoặc mẹ."
    ),
    params_schema=XacDinhNguoiTrucTiepNuoiConParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
