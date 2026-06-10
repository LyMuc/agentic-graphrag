"""Template — căn cứ đơn phương ly hôn (Đ56 K1, bổ trợ Đ19)."""
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

_ROUTER_FIELDS = ("can_cu",)
_DIEU_56_WHITELIST = ["Luat_HNGD_2014_Dieu_56"]
_DIEU_19_WHITELIST = ["Luat_HNGD_2014_Dieu_19"]

_CAN_CU_TO_DK = {
    "bao_luc_gia_dinh": "co_hanh_vi_bao_luc_gia_dinh",
    "vi_pham_nghiem_trong_quyen_nghia_vu": "vi_pham_nghiem_trong_quyen_nghia_vu_vo_chong",
    "ngoai_tinh": "ngoai_tinh_vi_pham_nghia_vu_chung_thuy",
    "co_bac_ruou_che_bo_mac": "co_bac_ruou_che_bo_mac_co_the_la_vi_pham_nghiem_trong",
    "mau_thuan_tram_trong": "hon_nhan_lam_vao_tinh_trang_tram_trong",
}

_HQ_MAP = {
    "tinh_trang_tram_trong": "hon_nhan_lam_vao_tinh_trang_tram_trong",
    "doi_song_khong_the_keo_dai": "doi_song_chung_khong_the_keo_dai",
    "muc_dich_khong_dat": "muc_dich_hon_nhan_khong_dat_duoc",
}


class CanCuDonPhuongLyHonParams(BaseModel):
    can_cu: Literal[
        "bao_luc_gia_dinh",
        "vi_pham_nghiem_trong_quyen_nghia_vu",
        "ngoai_tinh",
        "co_bac_ruou_che_bo_mac",
        "mau_thuan_tram_trong",
        "tong_quat",
        "khong_ro",
    ] = Field(
        description=(
            "Căn cứ nội dung Đ56 K1. Map: đánh đập → bao_luc_gia_dinh; "
            "ngoại tình → ngoai_tinh; cờ bạc/rượu chè → co_bac_ruou_che_bo_mac; "
            "liệt kê → tong_quat."
        )
    )
    chu_the_don_phuong: Literal["vo", "chong", "khong_ro"] = Field(
        description="Người muốn đơn phương."
    )
    hau_qua_hon_nhan: Literal[
        "tinh_trang_tram_trong",
        "doi_song_khong_the_keo_dai",
        "muc_dich_khong_dat",
        "day_du",
        "khong_ro",
    ] = Field(description="Hậu quả hôn nhân theo mô tả câu hỏi.")
    hoa_giai_tai_toa: Literal["khong_thanh", "chua_ro"] = Field(
        description="Hòa giải tại Tòa không thành → khong_thanh."
    )
    boi_canh_hon_nhan: Literal["dang_ly_than", "dang_song_chung", "khong_ro"] = Field(
        description="Ly thân/chuyển về nhà ngoại → dang_ly_than."
    )


_SEED_BODY = f"""
WITH $cc AS cc, $dk_id AS dk_id, $hq_ids AS hq_ids,
     $whitelist_dieu_ids AS wl

MATCH (ht:HinhThucLyHon:{TOPIC_LABEL} {{id: 'ly_hon_theo_yeu_cau_mot_ben', topic: '{TOPIC}'}})
OPTIONAL MATCH (hv:HanhVi:{TOPIC_LABEL} {{id: 'mot_ben_yeu_cau_ly_hon', topic: '{TOPIC}'}})
OPTIONAL MATCH (dk_hg:DieuKien:{TOPIC_LABEL} {{id: 'hoa_giai_tai_toa_khong_thanh', topic: '{TOPIC}'}})

OPTIONAL MATCH (dk:DieuKien:{TOPIC_LABEL} {{id: dk_id, topic: '{TOPIC}'}})
WHERE dk_id <> ''
OPTIONAL MATCH (nv:NghiaVu:{TOPIC_LABEL} {{id: 'nghia_vu_chung_thuy', topic: '{TOPIC}'}})
WHERE cc = 'ngoai_tinh'

OPTIONAL MATCH (dk_hq:DieuKien:{TOPIC_LABEL})
WHERE dk_hq.id IN hq_ids AND dk_hq.topic = '{TOPIC}'

OPTIONAL MATCH (hq:HauQua:{TOPIC_LABEL} {{id: 'toa_an_giai_quyet_cho_ly_hon_mot_ben', topic: '{TOPIC}'}})

WITH wl, cc,
  [x IN collect(DISTINCT ht) + collect(DISTINCT hv) + collect(DISTINCT dk_hg)
       + collect(DISTINCT dk) + collect(DISTINCT nv)
       + collect(DISTINCT dk_hq) + collect(DISTINCT hq)
   WHERE x IS NOT NULL] AS seed_nodes,
  CASE cc
    WHEN 'tong_quat' THEN
      [x IN collect(DISTINCT dk_hg) + collect(DISTINCT dk_hq) + collect(DISTINCT hq)
       WHERE x IS NOT NULL]
    WHEN 'khong_ro' THEN
      [x IN collect(DISTINCT dk_hg) + collect(DISTINCT dk) + collect(DISTINCT dk_hq)
           + collect(DISTINCT hq)
       WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT dk) + collect(DISTINCT nv)
           + collect(DISTINCT dk_hq) + collect(DISTINCT hq)
       WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: CanCuDonPhuongLyHonParams) -> dict[str, Any]:
    dk_id = _CAN_CU_TO_DK.get(params.can_cu, "")
    if params.hau_qua_hon_nhan == "day_du":
        hq_ids = list(_HQ_MAP.values())
    elif params.hau_qua_hon_nhan in _HQ_MAP:
        hq_ids = [_HQ_MAP[params.hau_qua_hon_nhan]]
    elif params.can_cu in ("tong_quat", "khong_ro"):
        hq_ids = list(_HQ_MAP.values())
    else:
        hq_ids = list(_HQ_MAP.values())

    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    seed_d19 = params.can_cu in ("ngoai_tinh", "co_bac_ruou_che_bo_mac", "tong_quat")
    whitelist: list[str] = []
    if use_wl:
        whitelist.extend(_DIEU_56_WHITELIST)
        if seed_d19:
            whitelist.extend(_DIEU_19_WHITELIST)
    return {
        "cc": params.can_cu,
        "dk_id": dk_id,
        "hq_ids": hq_ids,
        "whitelist_dieu_ids": whitelist,
    }


can_cu_don_phuong_ly_hon = CypherTemplate(
    name="can_cu_don_phuong_ly_hon",
    description=(
        "Căn cứ nội dung để Tòa án giải quyết ly hôn theo yêu cầu một bên (Đ56 K1): "
        "hòa giải không thành, bạo lực, vi phạm nghiêm trọng, hôn nhân trầm trọng. "
        "Ngoại tình, cờ bạc, ly thân là dữ kiện cần đánh giá, không tự động đủ căn cứ. "
        "Ví dụ: Các trường hợp đơn phương ly hôn; "
        "Ngoại tình có phải lý do đơn phương; "
        "Cờ bạc, rượu chè nhưng không đánh đập có được ly hôn không."
    ),
    params_schema=CanCuDonPhuongLyHonParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
