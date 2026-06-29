"""Template — quyền yêu cầu và hạn chế ly hôn (Đ51)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from server.infrastructure.neo4j.cypher_templates import CypherTemplate
from server.infrastructure.neo4j.cypher_templates.quy_dinh_chung_ly_hon._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("khia_canh_quyen",)
_DIEU_51_WHITELIST = ["Luat_HNGD_2014_Dieu_51"]

_CHU_THE_TO_ID = {
    "vo": "vo",
    "chong": "chong",
    "ca_hai": "ca_hai_vo_chong",
    "cha_me_nguoi_than_thich": "cha_me_nguoi_than_thich",
}

_TINH_TRANG_VO_CON_TO_DK = {
    "dang_co_thai": "vo_dang_co_thai",
    "dang_sinh_con": "vo_dang_sinh_con",
    "dang_nuoi_con_duoi_12_thang": "vo_dang_nuoi_con_duoi_12_thang",
}


class QuyenYeuCauVaHanCheLyHonParams(BaseModel):
    chu_the_yeu_cau: Literal[
        "vo", "chong", "ca_hai", "cha_me_nguoi_than_thich", "khong_ro"
    ] = Field(
        description=(
            "Chủ thể yêu cầu. Map: vợ/tôi là vợ → vo; chồng/anh ấy → chong; "
            "hai vợ chồng/cả hai → ca_hai; cha mẹ/người thân → cha_me_nguoi_than_thich; "
            "hỏi ai → khong_ro."
        )
    )
    tinh_trang_vo_con: Literal[
        "dang_co_thai",
        "dang_sinh_con",
        "dang_nuoi_con_duoi_12_thang",
        "khong_thuoc_han_che",
        "khong_ro",
    ] = Field(
        description=(
            "Tình trạng vợ/con liên quan hạn chế Đ51 K3. Map: mang thai/có bầu "
            "→ dang_co_thai; mới sinh → dang_sinh_con; con dưới 12 tháng "
            "→ dang_nuoi_con_duoi_12_thang."
        )
    )
    nang_luc_va_bao_luc: Literal[
        "mat_nang_luc_kem_bao_luc_nghiem_trong",
        "bao_luc_thong_thuong",
        "khong_co",
        "khong_ro",
    ] = Field(
        description=(
            "Mất năng lực kèm bạo lực nghiêm trọng → mat_nang_luc_kem_bao_luc_nghiem_trong; "
            "chỉ bạo hành thông thường → bao_luc_thong_thuong."
        )
    )
    boi_canh_yeu_cau: Literal["trong_nuoc", "co_yeu_to_nuoc_ngoai", "khong_ro"] = Field(
        description="Có yếu tố nước ngoài → co_yeu_to_nuoc_ngoai."
    )
    khia_canh_quyen: Literal[
        "chu_the_co_quyen",
        "han_che_quyen_cua_chong",
        "yeu_cau_thay_nguoi_mat_nang_luc",
        "tong_quat",
    ] = Field(
        description=(
            "Hỏi ai có quyền → chu_the_co_quyen; mang thai/mới sinh/con nhỏ "
            "→ han_che_quyen_cua_chong; cha mẹ thay người bệnh "
            "→ yeu_cau_thay_nguoi_mat_nang_luc."
        )
    )


_SEED_BODY = f"""
WITH $kc AS kc, $ct_id AS ct_id, $dk_id AS dk_id, $boi_canh AS bc,
     $seed_han_che AS sh, $seed_mat_nang_luc AS smn, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (ct:ChuThe:{TOPIC_LABEL} {{id: ct_id, topic: '{TOPIC}'}})
WHERE ct_id <> '' AND kc IN ['chu_the_co_quyen', 'tong_quat']

OPTIONAL MATCH (ct)-[:CO_QUYEN]->(q:Quyen:{TOPIC_LABEL})
WHERE ct IS NOT NULL

OPTIONAL MATCH (q_all:Quyen:{TOPIC_LABEL})
WHERE kc IN ['chu_the_co_quyen', 'tong_quat'] AND ct IS NULL AND q_all.topic = '{TOPIC}'

OPTIONAL MATCH (hc:Quyen:{TOPIC_LABEL} {{id: 'han_che_quyen_chong_yeu_cau_ly_hon', topic: '{TOPIC}'}})
WHERE sh = true
OPTIONAL MATCH (hc)-[:BI_HAN_CHE_KHI]->(dk:DieuKien:{TOPIC_LABEL} {{id: dk_id, topic: '{TOPIC}'}})
WHERE sh = true AND dk_id <> ''

OPTIONAL MATCH (qv:Quyen:{TOPIC_LABEL} {{id: 'quyen_vo_yeu_cau_ly_hon', topic: '{TOPIC}'}})
WHERE sh = true AND $chu_the = 'vo'

OPTIONAL MATCH (qcm:Quyen:{TOPIC_LABEL} {{id: 'quyen_cha_me_nguoi_than_yeu_cau_ly_hon', topic: '{TOPIC}'}})
WHERE smn = true
OPTIONAL MATCH (dk_mn:DieuKien:{TOPIC_LABEL})
WHERE smn = true AND dk_mn.id IN [
  'mot_ben_mat_nang_luc_nhan_thuc_lam_chu_hanh_vi',
  'nan_nhan_bao_luc_bi_anh_huong_nghiem_trong'
] AND dk_mn.topic = '{TOPIC}'
OPTIONAL MATCH (hq_bao_luc:HauQua:{TOPIC_LABEL} {{id: 'toa_an_giai_quyet_ly_hon_do_bao_luc_truong_hop_dac_biet', topic: '{TOPIC}'}})
WHERE smn = true

OPTIONAL MATCH (ht_nn:HinhThucLyHon:{TOPIC_LABEL} {{id: 'ly_hon_co_yeu_to_nuoc_ngoai', topic: '{TOPIC}'}})
WHERE bc = 'co_yeu_to_nuoc_ngoai'

WITH wl, kc,
  [x IN collect(DISTINCT ct) + collect(DISTINCT q) + collect(DISTINCT q_all)
       + collect(DISTINCT hc) + collect(DISTINCT dk) + collect(DISTINCT qv)
       + collect(DISTINCT qcm) + collect(DISTINCT dk_mn) + collect(DISTINCT hq_bao_luc)
       + collect(DISTINCT ht_nn)
   WHERE x IS NOT NULL] AS seed_nodes,
  CASE kc
    WHEN 'han_che_quyen_cua_chong' THEN
      [x IN collect(DISTINCT hc) + collect(DISTINCT dk) + collect(DISTINCT qv)
       WHERE x IS NOT NULL]
    WHEN 'yeu_cau_thay_nguoi_mat_nang_luc' THEN
      [x IN collect(DISTINCT qcm) + collect(DISTINCT dk_mn) + collect(DISTINCT hq_bao_luc)
       WHERE x IS NOT NULL]
    WHEN 'chu_the_co_quyen' THEN
      [x IN collect(DISTINCT q) + collect(DISTINCT q_all) WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT q_all) + collect(DISTINCT hc) + collect(DISTINCT ht_nn)
       WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: QuyenYeuCauVaHanCheLyHonParams) -> dict[str, Any]:
    ct_id = _CHU_THE_TO_ID.get(params.chu_the_yeu_cau, "")
    dk_id = _TINH_TRANG_VO_CON_TO_DK.get(params.tinh_trang_vo_con, "")
    seed_han_che = params.khia_canh_quyen == "han_che_quyen_cua_chong" or bool(dk_id)
    seed_mat_nang_luc = (
        params.khia_canh_quyen == "yeu_cau_thay_nguoi_mat_nang_luc"
        or params.nang_luc_va_bao_luc == "mat_nang_luc_kem_bao_luc_nghiem_trong"
    )
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "kc": params.khia_canh_quyen,
        "ct_id": ct_id,
        "dk_id": dk_id,
        "boi_canh": params.boi_canh_yeu_cau,
        "chu_the": params.chu_the_yeu_cau,
        "seed_han_che": seed_han_che,
        "seed_mat_nang_luc": seed_mat_nang_luc,
        "whitelist_dieu_ids": _DIEU_51_WHITELIST if use_wl else [],
    }


quyen_yeu_cau_va_han_che_ly_hon = CypherTemplate(
    name="quyen_yeu_cau_va_han_che_ly_hon",
    description=(
        "Xác định vợ, chồng, cả hai hoặc cha mẹ/người thân có quyền yêu cầu Tòa án "
        "giải quyết ly hôn và hạn chế riêng đối với chồng khi vợ mang thai, sinh con "
        "hoặc nuôi con dưới 12 tháng (Đ51). "
        "Ví dụ: Vợ đang mang thai thì chồng có được đơn phương ly hôn không; "
        "Vợ mới sinh con có được yêu cầu ly hôn không; "
        "Ai có quyền yêu cầu giải quyết ly hôn."
    ),
    params_schema=QuyenYeuCauVaHanCheLyHonParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
