"""Template — quyền yêu cầu hủy kết hôn trái pháp luật (Đ10)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from server.infrastructure.neo4j.cypher_templates import CypherTemplate
from server.infrastructure.neo4j.cypher_templates.ket_hon_trai_phap_luat._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("vai_tro_tham_gia",)
_TONG_QUAT_WHITELIST = ["Luat_HNGD_2014_Dieu_10"]

_CHU_THE_TO_ID = {
    "nguoi_bi_cuong_ep_lua_doi": "nguoi_bi_cuong_ep_hoac_lua_doi_ket_hon",
    "vo_chong_hop_phap_cua_nguoi_dang_co_vo_chong": "vo_chong_hop_phap_cua_nguoi_dang_co_vo_chong",
    "cha_me": "cha_me_con_nguoi_giam_ho_hoac_dai_dien_hop_phap",
    "cha": "cha_me_con_nguoi_giam_ho_hoac_dai_dien_hop_phap",
    "me": "cha_me_con_nguoi_giam_ho_hoac_dai_dien_hop_phap",
    "con": "cha_me_con_nguoi_giam_ho_hoac_dai_dien_hop_phap",
    "nguoi_giam_ho_dai_dien": "cha_me_con_nguoi_giam_ho_hoac_dai_dien_hop_phap",
    "co_quan_quan_ly_gia_dinh": "co_quan_quan_ly_nha_nuoc_ve_gia_dinh",
    "co_quan_quan_ly_tre_em": "co_quan_quan_ly_nha_nuoc_ve_tre_em",
    "hoi_lien_hiep_phu_nu": "hoi_lien_hiep_phu_nu",
    "nguoi_than_thich_khac": "ca_nhan_co_quan_to_chuc_khac_phat_hien_vi_pham",
    "ca_nhan_to_chuc_khac": "ca_nhan_co_quan_to_chuc_khac_phat_hien_vi_pham",
}


class QuyenYeuCauHuyKetHonTraiPhapLuatParams(BaseModel):
    nhom_vi_pham: Literal[
        "cuong_ep_khong_tu_nguyen",
        "lua_doi",
        "chua_du_tuoi",
        "dang_co_vo_chong",
        "mat_nang_luc_hanh_vi",
        "quan_he_bi_cam",
        "nhieu_vi_pham",
        "khong_ro",
    ] = Field(description="Nhóm vi phạm được kể trong câu hỏi.")
    chu_the_hoi_quyen: Literal[
        "nguoi_bi_cuong_ep_lua_doi",
        "vo_chong_hop_phap_cua_nguoi_dang_co_vo_chong",
        "cha_me",
        "cha",
        "me",
        "con",
        "nguoi_giam_ho_dai_dien",
        "co_quan_quan_ly_gia_dinh",
        "co_quan_quan_ly_tre_em",
        "hoi_lien_hiep_phu_nu",
        "nguoi_than_thich_khac",
        "ca_nhan_to_chuc_khac",
        "khong_ro",
    ] = Field(
        description=(
            "Chủ thể hỏi quyền. Map: tôi bị ép → nguoi_bi_cuong_ep_lua_doi; "
            "vợ/chồng hợp pháp → vo_chong_hop_phap...; cha/mẹ/con/giám hộ map trực tiếp; "
            "dì/chị/hàng xóm → nguoi_than_thich_khac/ca_nhan_to_chuc_khac."
        )
    )
    vai_tro_tham_gia: Literal[
        "tu_minh_yeu_cau",
        "yeu_cau_truc_tiep",
        "de_nghi_co_quan_to_chuc",
        "can_xac_dinh",
        "tong_quat",
    ] = Field(
        description=(
            "Vai trò tham gia. Map: tự mình yêu cầu → tu_minh_yeu_cau; "
            "có quyền yêu cầu trực tiếp → yeu_cau_truc_tiep; "
            "đề nghị cơ quan → de_nghi_co_quan_to_chuc; liệt kê → tong_quat."
        )
    )


_SEED_BODY = f"""
WITH $chu_the_id AS ct_id, $quyen_id AS q_id, $hanh_vi_id AS hv_id,
     $vai_tro AS vt, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (ct:ChuThe:{TOPIC_LABEL} {{id: ct_id, topic: '{TOPIC}'}})
WHERE ct_id <> ''
OPTIONAL MATCH (ct)-[:CO_QUYEN]->(q:Quyen:{TOPIC_LABEL})
WHERE ct_id <> '' AND (q_id = '' OR q.id = q_id)
OPTIONAL MATCH (q)-[:THUC_HIEN]->(hv:HanhVi:{TOPIC_LABEL})
WHERE q IS NOT NULL

OPTIONAL MATCH (ct_k3:ChuThe:{TOPIC_LABEL} {{id: 'ca_nhan_co_quan_to_chuc_khac_phat_hien_vi_pham', topic: '{TOPIC}'}})
WHERE ct_id IN ['ca_nhan_co_quan_to_chuc_khac_phat_hien_vi_pham', 'nguoi_than_thich_khac']
   OR vt = 'de_nghi_co_quan_to_chuc'
OPTIONAL MATCH (ct_k3)-[:CO_QUYEN]->(q_k3:Quyen:{TOPIC_LABEL} {{
  id: 'quyen_cua_chu_the_khac_de_nghi_co_quan_to_chuc_yeu_cau_huy', topic: '{TOPIC}'
}})
OPTIONAL MATCH (q_k3)-[:THUC_HIEN]->(hv_dn:HanhVi:{TOPIC_LABEL} {{
  id: 'de_nghi_co_quan_to_chuc_yeu_cau_huy', topic: '{TOPIC}'
}})

OPTIONAL MATCH (ct_ep:ChuThe:{TOPIC_LABEL} {{
  id: 'nguoi_bi_cuong_ep_hoac_lua_doi_ket_hon', topic: '{TOPIC}'
}})
WHERE vt IN ['tu_minh_yeu_cau', 'can_xac_dinh', 'tong_quat']
  AND ct_id IN ['nguoi_bi_cuong_ep_lua_doi', '']
OPTIONAL MATCH (ct_ep)-[:CO_QUYEN]->(q_ep:Quyen:{TOPIC_LABEL})
WHERE vt IN ['tu_minh_yeu_cau', 'can_xac_dinh', 'tong_quat']
OPTIONAL MATCH (q_ep)-[:THUC_HIEN]->(hv_ep:HanhVi:{TOPIC_LABEL})

WITH wl, vt, ct_id,
  collect(DISTINCT ct) + collect(DISTINCT q) + collect(DISTINCT hv)
    + collect(DISTINCT ct_k3) + collect(DISTINCT q_k3) + collect(DISTINCT hv_dn)
    + collect(DISTINCT ct_ep) + collect(DISTINCT q_ep) + collect(DISTINCT hv_ep) AS seed_nodes,
  CASE
    WHEN vt = 'de_nghi_co_quan_to_chuc'
         OR ct_id IN ['nguoi_than_thich_khac', 'ca_nhan_to_chuc_khac'] THEN
      [x IN collect(DISTINCT ct_k3) + collect(DISTINCT q_k3) + collect(DISTINCT hv_dn)
       WHERE x IS NOT NULL]
    WHEN vt = 'tu_minh_yeu_cau' OR ct_id = 'nguoi_bi_cuong_ep_lua_doi' THEN
      [x IN collect(DISTINCT ct_ep) + collect(DISTINCT q_ep) + collect(DISTINCT hv_ep)
       WHERE x IS NOT NULL]
    WHEN ct_id <> '' THEN
      [x IN collect(DISTINCT ct) + collect(DISTINCT q) + collect(DISTINCT hv)
       WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT ct) + collect(DISTINCT q) + collect(DISTINCT hv)
           + collect(DISTINCT ct_k3) + collect(DISTINCT q_k3) + collect(DISTINCT hv_dn)
           + collect(DISTINCT ct_ep) + collect(DISTINCT q_ep) + collect(DISTINCT hv_ep)
       WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _quyen_for_chu_the(chu_the: str, vai_tro: str) -> str:
    if chu_the in ("nguoi_than_thich_khac", "ca_nhan_to_chuc_khac") or vai_tro == "de_nghi_co_quan_to_chuc":
        return "quyen_cua_chu_the_khac_de_nghi_co_quan_to_chuc_yeu_cau_huy"
    if chu_the == "nguoi_bi_cuong_ep_lua_doi" or vai_tro == "tu_minh_yeu_cau":
        return "quyen_tu_minh_yeu_cau_huy_cua_nguoi_bi_cuong_ep_lua_doi"
    mapping = {
        "vo_chong_hop_phap_cua_nguoi_dang_co_vo_chong": "quyen_yeu_cau_huy_cua_vo_chong_cha_me_con_nguoi_giam_ho_dai_dien",
        "cha_me": "quyen_yeu_cau_huy_cua_vo_chong_cha_me_con_nguoi_giam_ho_dai_dien",
        "cha": "quyen_yeu_cau_huy_cua_vo_chong_cha_me_con_nguoi_giam_ho_dai_dien",
        "me": "quyen_yeu_cau_huy_cua_vo_chong_cha_me_con_nguoi_giam_ho_dai_dien",
        "con": "quyen_yeu_cau_huy_cua_vo_chong_cha_me_con_nguoi_giam_ho_dai_dien",
        "nguoi_giam_ho_dai_dien": "quyen_yeu_cau_huy_cua_vo_chong_cha_me_con_nguoi_giam_ho_dai_dien",
        "co_quan_quan_ly_gia_dinh": "quyen_yeu_cau_huy_cua_co_quan_quan_ly_gia_dinh",
        "co_quan_quan_ly_tre_em": "quyen_yeu_cau_huy_cua_co_quan_quan_ly_tre_em",
        "hoi_lien_hiep_phu_nu": "quyen_yeu_cau_huy_cua_hoi_lien_hiep_phu_nu",
    }
    return mapping.get(chu_the, "")


def _params_builder(params: QuyenYeuCauHuyKetHonTraiPhapLuatParams) -> dict[str, Any]:
    ct_id = _CHU_THE_TO_ID.get(params.chu_the_hoi_quyen, "")
    q_id = _quyen_for_chu_the(params.chu_the_hoi_quyen, params.vai_tro_tham_gia)
    hv_id = (
        "de_nghi_co_quan_to_chuc_yeu_cau_huy"
        if params.vai_tro_tham_gia == "de_nghi_co_quan_to_chuc"
        or params.chu_the_hoi_quyen in ("nguoi_than_thich_khac", "ca_nhan_to_chuc_khac")
        else "yeu_cau_toa_an_huy_ket_hon_trai_phap_luat"
    )
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "chu_the_id": ct_id,
        "quyen_id": q_id,
        "hanh_vi_id": hv_id,
        "vai_tro": params.vai_tro_tham_gia,
        "whitelist_dieu_ids": _TONG_QUAT_WHITELIST if use_wl else [],
    }


quyen_yeu_cau_huy_ket_hon_trai_phap_luat = CypherTemplate(
    name="quyen_yeu_cau_huy_ket_hon_trai_phap_luat",
    description=(
        "Xác định ai có quyền trực tiếp yêu cầu Tòa án hủy, ai có thể tự mình yêu cầu "
        "do bị cưỡng ép/lừa dối, và ai chỉ có quyền đề nghị cơ quan/tổ chức luật định. "
        "Phân biệt cha/mẹ/con/giám hộ với dì, chị, hàng xóm. "
        "Ví dụ: Người bị cưỡng ép có thể tự yêu cầu hay không?; "
        "Hàng xóm phát hiện tảo hôn có quyền yêu cầu không?"
    ),
    params_schema=QuyenYeuCauHuyKetHonTraiPhapLuatParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
