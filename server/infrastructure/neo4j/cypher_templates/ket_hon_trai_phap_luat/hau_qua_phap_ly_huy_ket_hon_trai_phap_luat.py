"""Template — hậu quả pháp lý sau khi hủy kết hôn trái pháp luật (Đ12)."""
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

_ROUTER_FIELDS = ("khia_canh_hau_qua",)
_TONG_QUAT_WHITELIST = ["Luat_HNGD_2014_Dieu_12"]

_KHIA_CANH_TO_HQ = {
    "cham_dut_quan_he_nhu_vo_chong": "hai_ben_phai_cham_dut_quan_he_nhu_vo_chong",
    "quyen_nghia_vu_cha_me_con": "quyen_nghia_vu_cha_me_con_giai_quyet_nhu_khi_ly_hon",
    "tai_san_nghia_vu_hop_dong": "tai_san_nghia_vu_hop_dong_giai_quyet_theo_dieu_16",
}


class HauQuaPhapLyHuyKetHonTraiPhapLuatParams(BaseModel):
    khia_canh_hau_qua: Literal[
        "cham_dut_quan_he_nhu_vo_chong",
        "quyen_nghia_vu_cha_me_con",
        "tai_san_nghia_vu_hop_dong",
        "tong_quat",
    ] = Field(
        description=(
            "Khía cạnh hậu quả. Map: chấm dứt quan hệ vợ chồng → cham_dut_quan_he_nhu_vo_chong; "
            "con chung/trách nhiệm với con → quyen_nghia_vu_cha_me_con; "
            "tài sản/nợ/hợp đồng → tai_san_nghia_vu_hop_dong; hậu quả gì → tong_quat."
        )
    )
    tinh_huong_quan_he: Literal[
        "da_bi_huy",
        "dang_ky_sai_tham_quyen",
        "khong_dang_ky",
        "khong_ro",
    ] = Field(
        description=(
            "Tình huống quan hệ. Chỉ dùng Điều 12 khi da_bi_huy; "
            "sai thẩm quyền/không đăng ký ưu tiên template thủ tục-phân loại."
        )
    )
    co_con_chung: Literal["co", "khong", "khong_ro"] = Field(
        description="Có nhắc con chung/con nhỏ."
    )
    co_tranh_chap_tai_san: Literal["co", "khong", "khong_ro"] = Field(
        description="Có hỏi chia tài sản, nhà đất, tiền, nợ."
    )
    co_yeu_cau_thua_ke: Literal["co", "khong", "khong_ro"] = Field(
        description="Có hỏi thừa kế/di sản — chỉ kích hoạt cảnh báo ranh giới."
    )


_SEED_BODY = f"""
WITH $khia_canh_hau_qua AS kchq, $hq_leaf_id AS hq_id, $tinh_huong AS th,
     $whitelist_dieu_ids AS wl

OPTIONAL MATCH (nhom:QuyDinh:{TOPIC_LABEL} {{
  id: 'nhom_hau_qua_huy_ket_hon_trai_phap_luat', topic: '{TOPIC}'
}})
WHERE th IN ['da_bi_huy', 'khong_ro'] AND kchq IN ['tong_quat', 'quyen_nghia_vu_cha_me_con',
  'tai_san_nghia_vu_hop_dong', 'cham_dut_quan_he_nhu_vo_chong']
OPTIONAL MATCH (nhom)-[:BAO_GOM]->(leaf:HauQua:{TOPIC_LABEL})
WHERE th IN ['da_bi_huy', 'khong_ro']
  AND (kchq = 'tong_quat' OR leaf.id = hq_id
       OR kchq = 'quyen_nghia_vu_cha_me_con' AND leaf.id = 'quyen_nghia_vu_cha_me_con_giai_quyet_nhu_khi_ly_hon'
       OR kchq = 'tai_san_nghia_vu_hop_dong' AND leaf.id = 'tai_san_nghia_vu_hop_dong_giai_quyet_theo_dieu_16'
       OR kchq = 'cham_dut_quan_he_nhu_vo_chong' AND leaf.id = 'hai_ben_phai_cham_dut_quan_he_nhu_vo_chong')

OPTIONAL MATCH (hv_huy:HanhVi:{TOPIC_LABEL} {{
  id: 'toa_an_quyet_dinh_huy_ket_hon_trai_phap_luat', topic: '{TOPIC}'
}})
WHERE th IN ['da_bi_huy', 'khong_ro']
OPTIONAL MATCH (hv_huy)-[:DAN_TOI]->(hq_hv:HauQua:{TOPIC_LABEL})
WHERE th IN ['da_bi_huy', 'khong_ro']
  AND (hq_id = '' OR hq_hv.id = hq_id OR kchq = 'tong_quat')
OPTIONAL MATCH (hq_hv)-[:XAC_LAP]->(tt:TinhTrangHonNhan:{TOPIC_LABEL} {{
  id: 'quan_he_ket_hon_trai_phap_luat_da_bi_huy', topic: '{TOPIC}'
}})
WHERE th IN ['da_bi_huy', 'khong_ro']

WITH wl, kchq, th, hq_id,
  collect(DISTINCT nhom) + collect(DISTINCT leaf)
    + collect(DISTINCT hv_huy) + collect(DISTINCT hq_hv) + collect(DISTINCT tt) AS seed_nodes,
  CASE
    WHEN kchq = 'tong_quat' THEN
      [x IN collect(DISTINCT nhom) + collect(DISTINCT leaf) WHERE x IS NOT NULL]
    WHEN hq_id <> '' THEN
      [x IN collect(DISTINCT leaf) + collect(DISTINCT hq_hv) WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT nhom) + collect(DISTINCT leaf) + collect(DISTINCT hq_hv)
       WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: HauQuaPhapLyHuyKetHonTraiPhapLuatParams) -> dict[str, Any]:
    hq_id = _KHIA_CANH_TO_HQ.get(params.khia_canh_hau_qua, "")
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    if params.tinh_huong_quan_he in ("dang_ky_sai_tham_quyen", "khong_dang_ky"):
        use_wl = False
        hq_id = ""
    return {
        "khia_canh_hau_qua": params.khia_canh_hau_qua,
        "hq_leaf_id": hq_id,
        "tinh_huong": params.tinh_huong_quan_he,
        "whitelist_dieu_ids": _TONG_QUAT_WHITELIST if use_wl else [],
    }


hau_qua_phap_ly_huy_ket_hon_trai_phap_luat = CypherTemplate(
    name="hau_qua_phap_ly_huy_ket_hon_trai_phap_luat",
    description=(
        "Hậu quả sau khi Tòa án đã hủy: chấm dứt quan hệ vợ chồng; quyền nghĩa vụ cha mẹ con "
        "như khi ly hôn; tài sản, nghĩa vụ và hợp đồng theo Điều 16 (không tự kết luận thừa kế). "
        "Ví dụ: Hậu quả pháp lý chung của việc hủy là gì?; "
        "Giải quyết tài sản giữa các bên sau khi hủy thế nào?"
    ),
    params_schema=HauQuaPhapLyHuyKetHonTraiPhapLuatParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
