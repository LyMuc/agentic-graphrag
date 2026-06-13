"""Template — ảnh hưởng án treo, án tích, khuyết tật đến quyền kết hôn (Đ8)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.dieu_kien_ket_hon._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("khia_canh_anh_huong",)
_DIEU_WHITELIST = ["Luat_HNGD_2014_Dieu_5", "Luat_HNGD_2014_Dieu_8"]

_HOAN_CANH_QD: dict[str, str] = {
    "dang_chap_hanh_an_treo": "an_treo_khong_tu_dong_la_tro_ngai_ket_hon",
    "chua_duoc_xoa_an_tich": "an_tich_chua_duoc_xoa_khong_tu_dong_la_tro_ngai_ket_hon",
    "bai_liet_hoac_khuyet_tat_the_chat": "bai_liet_khong_dong_nghia_mat_nang_luc_hanh_vi_dan_su",
    "bi_mat_nang_luc_hanh_vi_dan_su": "bai_liet_khong_dong_nghia_mat_nang_luc_hanh_vi_dan_su",
}


class AnhHuongTinhTrangCaNhanParams(BaseModel):
    hoan_canh_ca_nhan: Literal[
        "dang_chap_hanh_an_treo",
        "bai_liet_hoac_khuyet_tat_the_chat",
        "chua_duoc_xoa_an_tich",
        "bi_mat_nang_luc_hanh_vi_dan_su",
        "khong_ro",
    ] = Field(
        description=(
            "án treo -> dang_chap_hanh_an_treo; "
            "bại liệt/khuyết tật -> bai_liet_hoac_khuyet_tat_the_chat; "
            "chưa xóa án tích -> chua_duoc_xoa_an_tich."
        )
    )
    tinh_trang_nang_luc_hanh_vi: Literal["khong_bi_mat", "bi_mat", "khong_ro"] = Field(
        description=(
            "mất năng lực hành vi dân sự -> bi_mat; "
            "chỉ bệnh/khuyết tật thể chất -> khong_ro; "
            "vẫn nhận thức làm chủ -> khong_bi_mat."
        )
    )
    khia_canh_anh_huong: Literal[
        "co_tu_dong_bi_cam",
        "co_duoc_ket_hon",
        "can_kiem_tra_dieu_kien_nao",
        "tong_quat",
    ] = Field(
        description=(
            "có được không -> co_duoc_ket_hon; "
            "có bị cấm -> co_tu_dong_bi_cam; "
            "cần kiểm tra gì -> can_kiem_tra_dieu_kien_nao."
        )
    )


_SEED_BODY = f"""
WITH $qd_id AS qd_id, $hc AS hc, $kc AS kc, $nl AS nl,
     $seed_dk AS seed_dk, $seed_khong_dk AS seed_khong_dk,
     $seed_tong_quat AS seed_tong_quat, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (qd:QuyDinh:{TOPIC_LABEL} {{id: qd_id, topic: '{TOPIC}'}})
WHERE qd_id <> ''

OPTIONAL MATCH (dk_nl:DieuKien:{TOPIC_LABEL} {{
  id: 'khong_bi_mat_nang_luc_hanh_vi_dan_su', topic: '{TOPIC}'
}})
WHERE hc = 'bai_liet_hoac_khuyet_tat_the_chat'
   OR nl IN ['khong_bi_mat', 'khong_ro', 'bi_mat']

OPTIONAL MATCH (dk:DieuKien:{TOPIC_LABEL} {{id: 'du_dieu_kien_ket_hon', topic: '{TOPIC}'}})
WHERE seed_dk = true

OPTIONAL MATCH (hq_kd:HauQua:{TOPIC_LABEL} {{id: 'khong_du_dieu_kien_ket_hon', topic: '{TOPIC}'}})
WHERE seed_khong_dk = true

OPTIONAL MATCH (qd_cam:QuyDinh:{TOPIC_LABEL} {{
  id: 'cac_truong_hop_cam_ket_hon_diem_a_den_d', topic: '{TOPIC}'
}})
WHERE seed_tong_quat = true

WITH wl, kc,
  [x IN collect(DISTINCT qd) + collect(DISTINCT dk_nl) + collect(DISTINCT dk)
       + collect(DISTINCT hq_kd) + collect(DISTINCT qd_cam)
   WHERE x IS NOT NULL] AS seed_nodes,
  CASE
    WHEN seed_khong_dk = true THEN
      [x IN collect(DISTINCT dk_nl) + collect(DISTINCT hq_kd) WHERE x IS NOT NULL]
    WHEN hc = 'bai_liet_hoac_khuyet_tat_the_chat' THEN
      [x IN collect(DISTINCT qd) + collect(DISTINCT dk_nl) WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT qd) + collect(DISTINCT dk) + collect(DISTINCT qd_cam)
       WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: AnhHuongTinhTrangCaNhanParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    hc = params.hoan_canh_ca_nhan
    nl = params.tinh_trang_nang_luc_hanh_vi
    if nl == "bi_mat" or hc == "bi_mat_nang_luc_hanh_vi_dan_su":
        qd_id = _HOAN_CANH_QD["bi_mat_nang_luc_hanh_vi_dan_su"]
        seed_khong_dk = True
        seed_dk = False
    else:
        qd_id = _HOAN_CANH_QD.get(hc, "")
        seed_khong_dk = False
        seed_dk = params.khia_canh_anh_huong in (
            "co_duoc_ket_hon",
            "can_kiem_tra_dieu_kien_nao",
            "tong_quat",
        )
    seed_tong_quat = params.khia_canh_anh_huong == "tong_quat" and hc in (
        "dang_chap_hanh_an_treo",
        "chua_duoc_xoa_an_tich",
        "khong_ro",
    )
    return {
        "qd_id": qd_id,
        "hc": hc,
        "kc": params.khia_canh_anh_huong,
        "nl": nl,
        "seed_dk": seed_dk,
        "seed_khong_dk": seed_khong_dk,
        "seed_tong_quat": seed_tong_quat,
        "whitelist_dieu_ids": _DIEU_WHITELIST if use_wl else [],
    }


anh_huong_tinh_trang_ca_nhan = CypherTemplate(
    name="anh_huong_tinh_trang_ca_nhan",
    description=(
        "Đánh giá án treo, án tích hoặc khuyết tật thể chất có tự động làm mất quyền "
        "kết hôn hay không bằng cách đối chiếu danh sách Điều 8. Template không suy "
        "luận bại liệt là mất năng lực hành vi dân sự; chỉ seed điểm c khi cần. "
        "Ví dụ: Người đang chấp hành án treo có được kết hôn không?; "
        "Người chưa được xóa án tích có được kết hôn không?"
    ),
    params_schema=AnhHuongTinhTrangCaNhanParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
