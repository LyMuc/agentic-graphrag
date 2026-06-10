"""Template — nơi và thẩm quyền đăng ký kết hôn (Đ17, Đ37, Đ11 Luật Cư trú)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.dang_ky_ket_hon._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("boi_canh_chu_the",)
_DIEU_WHITELIST = ["Luat_HoTich_2014_Dieu_17", "Luat_HoTich_2014_Dieu_37"]

_CHU_THE_MAP = {
    "trong_nuoc": (
        "cong_dan_viet_nam_cu_tru_trong_nuoc",
        "ubnd_cap_xa_noi_cu_tru_mot_trong_hai_ben",
    ),
    "cong_dan_vn_voi_nguoi_nuoc_ngoai": (
        "cong_dan_viet_nam_voi_nguoi_nuoc_ngoai",
        "ubnd_cap_huyen_noi_cu_tru_cong_dan_viet_nam",
    ),
    "cong_dan_vn_dinh_cu_o_nuoc_ngoai": (
        "cong_dan_viet_nam_dinh_cu_o_nuoc_ngoai",
        "ubnd_cap_huyen_noi_cu_tru_cong_dan_viet_nam",
    ),
    "nguoi_nuoc_ngoai_cu_tru_vn": (
        "nguoi_nuoc_ngoai_cu_tru_tai_viet_nam",
        "ubnd_cap_huyen_noi_cu_tru_mot_trong_hai_ben",
    ),
}

_NOI_CU_TRU_MAP = {
    "thuong_tru": "noi_thuong_tru",
    "tam_tru": "noi_tam_tru",
    "noi_o_hien_tai": "noi_o_hien_tai_khi_khong_xac_dinh_duoc_cu_tru",
}


class NoiVaThamQuyenDangKyKetHonParams(BaseModel):
    boi_canh_chu_the: Literal[
        "trong_nuoc",
        "cong_dan_vn_voi_nguoi_nuoc_ngoai",
        "cong_dan_vn_dinh_cu_o_nuoc_ngoai",
        "nguoi_nuoc_ngoai_cu_tru_vn",
        "khong_ro",
    ] = Field(
        description=(
            "Hai công dân Việt Nam trong nước -> trong_nuoc; kết hôn với người nước ngoài "
            "-> cong_dan_vn_voi_nguoi_nuoc_ngoai; Việt kiều/định cư nước ngoài "
            "-> cong_dan_vn_dinh_cu_o_nuoc_ngoai; hai người nước ngoài ở VN "
            "-> nguoi_nuoc_ngoai_cu_tru_vn."
        )
    )
    loai_noi_cu_tru: Literal[
        "thuong_tru", "tam_tru", "noi_o_hien_tai", "khong_ro"
    ] = Field(
        description=(
            "Hộ khẩu/thường trú -> thuong_tru; tạm trú/KT3 -> tam_tru; "
            "nơi ở hiện tại không xác định được cư trú -> noi_o_hien_tai."
        )
    )
    ben_co_noi_cu_tru: Literal["ben_nam", "ben_nu", "mot_trong_hai", "khong_ro"] = Field(
        description=(
            "Nhà chồng/bên nam -> ben_nam; nhà vợ/bên nữ -> ben_nu; "
            "một trong hai hoặc hỏi chung -> mot_trong_hai."
        )
    )
    khia_canh_tham_quyen: Literal[
        "dia_diem",
        "co_quan",
        "cap_co_quan",
        "co_duoc_dang_ky_tai_noi_nay",
        "tong_quat",
    ] = Field(
        description=(
            "Ở đâu/nơi nào -> dia_diem; cơ quan nào -> co_quan; cấp xã/huyện -> cap_co_quan; "
            "có được đăng ký ở... -> co_duoc_dang_ky_tai_noi_nay."
        )
    )
    tinh_huong_ket_hon: Literal[
        "lan_dau", "ket_hon_lai_sau_ly_hon", "khong_ro"
    ] = Field(
        description="Kết hôn lại sau ly hôn -> ket_hon_lai_sau_ly_hon; lần đầu -> lan_dau."
    )


_SEED_BODY = f"""
WITH $bc AS bc, $ct_id AS ct_id, $cq_id AS cq_id, $nct_id AS nct_id,
     $seed_both AS sb, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (ct:ChuThe:{TOPIC_LABEL} {{id: ct_id, topic: '{TOPIC}'}})
WHERE ct_id <> ''

OPTIONAL MATCH (ct)-[:DANG_KY_TAI]->(cq:CoQuanDangKy:{TOPIC_LABEL} {{id: cq_id, topic: '{TOPIC}'}})
WHERE cq_id <> ''

OPTIONAL MATCH (cq_xa:CoQuanDangKy:{TOPIC_LABEL} {{id: 'ubnd_cap_xa_noi_cu_tru_mot_trong_hai_ben', topic: '{TOPIC}'}})
WHERE sb = true
OPTIONAL MATCH (cq_huyen_vn:CoQuanDangKy:{TOPIC_LABEL} {{id: 'ubnd_cap_huyen_noi_cu_tru_cong_dan_viet_nam', topic: '{TOPIC}'}})
WHERE sb = true
OPTIONAL MATCH (cq_huyen_nn:CoQuanDangKy:{TOPIC_LABEL} {{id: 'ubnd_cap_huyen_noi_cu_tru_mot_trong_hai_ben', topic: '{TOPIC}'}})
WHERE sb = true

OPTIONAL MATCH (nc:NoiCuTru:{TOPIC_LABEL} {{id: nct_id, topic: '{TOPIC}'}})
WHERE nct_id <> ''

OPTIONAL MATCH (cq)-[:CO_THAM_QUYEN_TAI]->(nc2:NoiCuTru:{TOPIC_LABEL})
WHERE cq IS NOT NULL AND nc2.topic = '{TOPIC}'

WITH wl, bc,
  [x IN collect(DISTINCT ct) + collect(DISTINCT cq)
       + collect(DISTINCT cq_xa) + collect(DISTINCT cq_huyen_vn)
       + collect(DISTINCT cq_huyen_nn) + collect(DISTINCT nc)
       + collect(DISTINCT nc2)
   WHERE x IS NOT NULL] AS seed_nodes,
  [x IN collect(DISTINCT cq) + collect(DISTINCT cq_xa)
       + collect(DISTINCT cq_huyen_vn) + collect(DISTINCT cq_huyen_nn)
       + collect(DISTINCT nc) + collect(DISTINCT nc2)
   WHERE x IS NOT NULL] AS leaf_seed_nodes
"""


def _params_builder(params: NoiVaThamQuyenDangKyKetHonParams) -> dict[str, Any]:
    ct_id, cq_id = _CHU_THE_MAP.get(params.boi_canh_chu_the, ("", ""))
    nct_id = _NOI_CU_TRU_MAP.get(params.loai_noi_cu_tru, "")
    seed_both = params.boi_canh_chu_the == "khong_ro"
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "bc": params.boi_canh_chu_the,
        "ct_id": ct_id,
        "cq_id": cq_id,
        "nct_id": nct_id,
        "seed_both": seed_both,
        "whitelist_dieu_ids": _DIEU_WHITELIST if use_wl else [],
    }


noi_va_tham_quyen_dang_ky_ket_hon = CypherTemplate(
    name="noi_va_tham_quyen_dang_ky_ket_hon",
    description=(
        "Trả lời nơi đăng ký, cơ quan/cấp có thẩm quyền và việc có thể đăng ký tại thường trú, "
        "tạm trú, nhà vợ/chồng hoặc khi hai bên khác tỉnh (Đ17, Đ37, Đ11 Luật Cư trú). "
        "Ví dụ: Đăng ký kết hôn tại nơi tạm trú được không?; "
        "Cơ quan nào có thẩm quyền đăng ký kết hôn?; "
        "Đăng ký kết hôn ở đâu?"
    ),
    params_schema=NoiVaThamQuyenDangKyKetHonParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
