"""Template — kết hôn có yếu tố nước ngoài (Đ126)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from server.infrastructure.neo4j.cypher_templates import CypherTemplate
from server.infrastructure.neo4j.cypher_templates.quan_he_hon_nhan_co_yeu_to_nuoc_ngoai._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("nhom_chu_the",)
_DIEU_WHITELIST = [
    "Luat_HNGD_2014_Dieu_126",
    "Luat_HNGD_2014_Dieu_8",
    "Luat_HNGD_2014_Dieu_5_Khoan_2_Diem_a",
    "Luat_HNGD_2014_Dieu_5_Khoan_2_Diem_b",
    "Luat_HNGD_2014_Dieu_5_Khoan_2_Diem_c",
    "Luat_HNGD_2014_Dieu_5_Khoan_2_Diem_d",
]


class KetHonYeuToNuocNgoaiParams(BaseModel):
    nhom_chu_the: Literal[
        "cong_dan_viet_nam_voi_nguoi_nuoc_ngoai",
        "hai_nguoi_nuoc_ngoai_thuong_tru_tai_viet_nam",
        "khong_ro",
    ] = Field(description="VN-người nước ngoài / hai người nước ngoài thường trú VN.")
    noi_tien_hanh_ket_hon: Literal[
        "co_quan_co_tham_quyen_viet_nam",
        "ngoai_viet_nam",
        "khong_ro",
    ] = Field(description="đăng ký tại Việt Nam → co_quan_co_tham_quyen_viet_nam.")
    ben_can_xet: Literal[
        "cong_dan_viet_nam",
        "nguoi_nuoc_ngoai",
        "moi_ben",
        "ca_hai_nguoi_nuoc_ngoai",
        "khong_ro",
    ] = Field(description="mỗi bên theo luật nước nào → moi_ben.")
    khia_canh_ket_hon: Literal[
        "phap_luat_dieu_kien_ket_hon",
        "dieu_kien_bo_sung_tai_viet_nam",
        "tong_quat",
    ] = Field(description="điều kiện bổ sung tại cơ quan Việt Nam → dieu_kien_bo_sung_tai_viet_nam.")


_SEED_BODY = f"""
WITH $nhom_chu_the AS nc, $noi_tien_hanh_ket_hon AS nt, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (l_vn:QuanHe:{TOPIC_LABEL} {{
  id: 'ket_hon_cong_dan_viet_nam_voi_nguoi_nuoc_ngoai', topic: '{TOPIC}'
}})
WHERE nc IN ['cong_dan_viet_nam_voi_nguoi_nuoc_ngoai', 'khong_ro']
OPTIONAL MATCH (l_vn_dk:DieuKien:{TOPIC_LABEL} {{
  id: 'moi_ben_tuan_phap_luat_nuoc_minh_ve_dieu_kien_ket_hon', topic: '{TOPIC}'
}})
WHERE nc IN ['cong_dan_viet_nam_voi_nguoi_nuoc_ngoai', 'khong_ro']
OPTIONAL MATCH (l_vn_hv:HanhVi:{TOPIC_LABEL} {{
  id: 'ket_hon_tai_co_quan_co_tham_quyen_viet_nam', topic: '{TOPIC}'
}})
WHERE nc IN ['cong_dan_viet_nam_voi_nguoi_nuoc_ngoai', 'khong_ro']
  AND nt IN ['co_quan_co_tham_quyen_viet_nam', 'khong_ro']
OPTIONAL MATCH (l_vn_bs:DieuKien:{TOPIC_LABEL} {{
  id: 'nguoi_nuoc_ngoai_tuan_them_dieu_kien_ket_hon_viet_nam', topic: '{TOPIC}'
}})
WHERE nc IN ['cong_dan_viet_nam_voi_nguoi_nuoc_ngoai', 'khong_ro']
  AND nt IN ['co_quan_co_tham_quyen_viet_nam', 'khong_ro']

OPTIONAL MATCH (l_nn:ChuThe:{TOPIC_LABEL} {{
  id: 'hai_nguoi_nuoc_ngoai_thuong_tru_tai_viet_nam', topic: '{TOPIC}'
}})
WHERE nc IN ['hai_nguoi_nuoc_ngoai_thuong_tru_tai_viet_nam', 'khong_ro']
OPTIONAL MATCH (l_nn_dk:DieuKien:{TOPIC_LABEL} {{
  id: 'tuan_dieu_kien_ket_hon_viet_nam', topic: '{TOPIC}'
}})
WHERE nc IN ['hai_nguoi_nuoc_ngoai_thuong_tru_tai_viet_nam', 'khong_ro']

WITH wl, nc, nt,
  collect(DISTINCT l_vn) + collect(DISTINCT l_vn_dk)
    + collect(DISTINCT l_vn_hv) + collect(DISTINCT l_vn_bs)
    + collect(DISTINCT l_nn) + collect(DISTINCT l_nn_dk) AS seed_nodes,
  CASE
    WHEN nc = 'hai_nguoi_nuoc_ngoai_thuong_tru_tai_viet_nam' THEN
      [x IN collect(DISTINCT l_nn) + collect(DISTINCT l_nn_dk) WHERE x IS NOT NULL]
    WHEN nc = 'cong_dan_viet_nam_voi_nguoi_nuoc_ngoai'
         AND nt = 'co_quan_co_tham_quyen_viet_nam' THEN
      [x IN collect(DISTINCT l_vn) + collect(DISTINCT l_vn_dk)
           + collect(DISTINCT l_vn_hv) + collect(DISTINCT l_vn_bs)
       WHERE x IS NOT NULL]
    WHEN nc = 'cong_dan_viet_nam_voi_nguoi_nuoc_ngoai' THEN
      [x IN collect(DISTINCT l_vn) + collect(DISTINCT l_vn_dk) WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT l_vn) + collect(DISTINCT l_vn_dk)
           + collect(DISTINCT l_nn) + collect(DISTINCT l_nn_dk)
       WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: KetHonYeuToNuocNgoaiParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "nhom_chu_the": params.nhom_chu_the,
        "noi_tien_hanh_ket_hon": params.noi_tien_hanh_ket_hon,
        "whitelist_dieu_ids": _DIEU_WHITELIST if use_wl else [],
    }


ket_hon_co_yeu_to_nuoc_ngoai = CypherTemplate(
    name="ket_hon_co_yeu_to_nuoc_ngoai",
    description=(
        "Dùng cho điều kiện kết hôn giữa công dân Việt Nam với người nước ngoài hoặc "
        "giữa hai người nước ngoài thường trú tại Việt Nam. Phân biệt luật của mỗi bên "
        "với nghĩa vụ tuân điều kiện kết hôn Việt Nam khi thực hiện tại cơ quan Việt Nam. "
        "Ví dụ: Công dân Việt Nam và người Mỹ đăng ký kết hôn tại Việt Nam tuân luật nào?; "
        "Hai người nước ngoài thường trú tại Việt Nam kết hôn phải đáp ứng gì?"
    ),
    params_schema=KetHonYeuToNuocNgoaiParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
