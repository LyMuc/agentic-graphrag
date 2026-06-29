"""Template — khái niệm và căn cứ hủy kết hôn trái pháp luật (Đ3 K6, TTLT Đ2)."""
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

_ROUTER_FIELDS = ("khia_canh",)
_TONG_QUAT_WHITELIST = [
    "Luat_HNGD_2014_Dieu_3_Khoan_6",
    "ThongTuLienTich_01_2016_TTLT_TANDTC_VKSNDTC_BTP_Dieu_2",
]

_DANG_VI_PHAM_TO_DK = {
    "chua_du_tuoi": "vi_pham_dieu_kien_tuoi_ket_hon",
    "khong_tu_nguyen_cuong_ep": "vi_pham_dieu_kien_tu_nguyen_ket_hon",
    "lua_doi": "bi_lua_doi_dan_den_dong_y_ket_hon",
    "dang_co_vo_chong": "vi_pham_do_mot_ben_dang_co_vo_hoac_chong",
    "dieu_kien_khac": "vi_pham_dieu_kien_ket_hon_khac_can_doi_chieu_dieu_8",
}


class KhaiNiemVaCanCuKetHonTraiPhapLuatParams(BaseModel):
    khia_canh: Literal[
        "khai_niem",
        "truong_hop_vi_pham",
        "can_cu_huy",
        "ranh_gioi_hanh_vi_bi_cam",
        "tong_quat",
    ] = Field(
        description=(
            "Khía cạnh câu hỏi. Map: là gì/thế nào → khai_niem; trường hợp nào → "
            "truong_hop_vi_pham; căn cứ hủy → can_cu_huy; hợp đồng hôn nhân/xử phạt "
            "→ ranh_gioi_hanh_vi_bi_cam; câu rộng → tong_quat."
        )
    )
    dang_vi_pham: Literal[
        "chua_du_tuoi",
        "khong_tu_nguyen_cuong_ep",
        "lua_doi",
        "dang_co_vo_chong",
        "dieu_kien_khac",
        "ket_hon_gia_tao_ngoai_core",
        "khong_ro",
    ] = Field(
        description=(
            "Loại vi phạm được nêu. Map: tảo hôn/chưa đủ tuổi → chua_du_tuoi; "
            "ép buộc/cưỡng ép → khong_tu_nguyen_cuong_ep; lừa dối → lua_doi; "
            "đã có vợ/chồng → dang_co_vo_chong; kết hôn giả nhập cư → ket_hon_gia_tao_ngoai_core."
        )
    )
    tinh_trang_dang_ky: Literal[
        "dung_tham_quyen",
        "sai_tham_quyen",
        "khong_dang_ky",
        "khong_ro",
    ] = Field(
        description=(
            "Tình trạng đăng ký. Map: đã cấp giấy đúng cơ quan → dung_tham_quyen; "
            "sai thẩm quyền → sai_tham_quyen; chưa đăng ký/chỉ sống chung → khong_dang_ky."
        )
    )


_SEED_BODY = f"""
WITH $khia_canh AS kc, $dang_vi_pham AS dvp, $dk_vi_pham_id AS dk_id,
     $tinh_trang_dang_ky AS ttdk, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (qd:QuyDinh:{TOPIC_LABEL} {{id: 'dinh_nghia_ket_hon_trai_phap_luat', topic: '{TOPIC}'}})
WHERE kc IN ['khai_niem', 'truong_hop_vi_pham', 'ranh_gioi_hanh_vi_bi_cam', 'tong_quat']
OPTIONAL MATCH (qd)-[:BAO_GOM]->(dk_dk:DieuKien:{TOPIC_LABEL})
WHERE kc IN ['khai_niem', 'tong_quat']
  AND (ttdk = 'dung_tham_quyen' AND dk_dk.id = 'da_dang_ky_ket_hon_dung_co_quan_co_tham_quyen'
       OR ttdk = 'khong_ro' AND dk_dk.id IN [
         'da_dang_ky_ket_hon_dung_co_quan_co_tham_quyen',
         'dang_ky_ket_hon_sai_co_quan_co_tham_quyen',
         'chung_song_nhu_vo_chong_khong_dang_ky_ket_hon'
       ])

OPTIONAL MATCH (cc:QuyDinh:{TOPIC_LABEL} {{id: 'can_cu_huy_ket_hon_trai_phap_luat', topic: '{TOPIC}'}})
WHERE kc IN ['truong_hop_vi_pham', 'can_cu_huy', 'ranh_gioi_hanh_vi_bi_cam', 'tong_quat']
OPTIONAL MATCH (cc)-[:BAO_GOM]->(leaf_vp:DieuKien:{TOPIC_LABEL})
WHERE kc IN ['truong_hop_vi_pham', 'can_cu_huy']
  AND (dvp <> 'khong_ro' AND leaf_vp.id = dk_id
       OR dvp IN ['khong_ro', 'ket_hon_gia_tao_ngoai_core'] AND leaf_vp IS NOT NULL)

WITH wl, kc, dvp, ttdk,
  collect(DISTINCT qd) + collect(DISTINCT dk_dk) + collect(DISTINCT cc) AS seed_nodes,
  CASE
    WHEN kc = 'can_cu_huy' THEN
      [x IN collect(DISTINCT cc) + collect(DISTINCT leaf_vp) WHERE x IS NOT NULL]
    WHEN kc = 'truong_hop_vi_pham' AND dvp <> 'khong_ro' AND dvp <> 'ket_hon_gia_tao_ngoai_core' THEN
      [x IN collect(DISTINCT leaf_vp) WHERE x IS NOT NULL]
    WHEN kc = 'khai_niem' THEN
      [x IN collect(DISTINCT qd) + collect(DISTINCT dk_dk) WHERE x IS NOT NULL]
    WHEN kc = 'ranh_gioi_hanh_vi_bi_cam' THEN
      [x IN collect(DISTINCT qd) + collect(DISTINCT cc) WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT qd) + collect(DISTINCT dk_dk)
           + collect(DISTINCT cc) + collect(DISTINCT leaf_vp)
       WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: KhaiNiemVaCanCuKetHonTraiPhapLuatParams) -> dict[str, Any]:
    dk_id = _DANG_VI_PHAM_TO_DK.get(params.dang_vi_pham, "")
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS) or params.khia_canh == "tong_quat"
    return {
        "khia_canh": params.khia_canh,
        "dang_vi_pham": params.dang_vi_pham,
        "dk_vi_pham_id": dk_id,
        "tinh_trang_dang_ky": params.tinh_trang_dang_ky,
        "whitelist_dieu_ids": _TONG_QUAT_WHITELIST if use_wl else [],
    }


khai_niem_va_can_cu_ket_hon_trai_phap_luat = CypherTemplate(
    name="khai_niem_va_can_cu_ket_hon_trai_phap_luat",
    description=(
        "Giải thích định nghĩa kết hôn trái pháp luật và các nhóm căn cứ Tòa án dùng "
        "để xem xét hủy. Dùng khi hỏi là gì, trường hợp nào, căn cứ hủy; với kết hôn "
        "giả tạo chỉ xác định ranh giới core, không mở rộng xử phạt Điều 5. "
        "Ví dụ: Trong trường hợp nào được xem là kết hôn trái pháp luật?; "
        "Căn cứ để hủy kết hôn trái pháp luật là gì?"
    ),
    params_schema=KhaiNiemVaCanCuKetHonTraiPhapLuatParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
