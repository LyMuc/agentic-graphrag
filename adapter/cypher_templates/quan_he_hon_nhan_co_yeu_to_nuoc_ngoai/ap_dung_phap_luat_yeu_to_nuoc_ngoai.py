"""Template — nguyên tắc áp dụng pháp luật có yếu tố nước ngoài (Đ122)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.quan_he_hon_nhan_co_yeu_to_nuoc_ngoai._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("co_so_ap_dung",)
_DIEU_WHITELIST = ["Luat_HNGD_2014_Dieu_122"]


class ApDungPhapLuatParams(BaseModel):
    co_so_ap_dung: Literal[
        "mac_dinh_phap_luat_viet_nam",
        "dieu_uoc_quoc_te_co_quy_dinh_khac",
        "phap_luat_viet_nam_dan_chieu",
        "dieu_uoc_quoc_te_dan_chieu",
        "tat_ca_truong_hop_dan_chieu",
        "phap_luat_nuoc_ngoai_dan_chieu_tro_lai",
        "khong_ro",
    ] = Field(
        description=(
            "điều ước quốc tế khác Luật → dieu_uoc_quoc_te_co_quy_dinh_khac; "
            "VN dẫn chiếu luật nước ngoài → phap_luat_viet_nam_dan_chieu; "
            "điều ước dẫn chiếu → dieu_uoc_quoc_te_dan_chieu; "
            "khi nào áp dụng luật nước ngoài → tat_ca_truong_hop_dan_chieu; "
            "dẫn chiếu trở lại VN → phap_luat_nuoc_ngoai_dan_chieu_tro_lai."
        )
    )
    khia_canh_ap_dung: Literal[
        "phap_luat_duoc_ap_dung",
        "dieu_kien_ap_dung_phap_luat_nuoc_ngoai",
        "dan_chieu_tro_lai",
        "tong_quat",
    ] = Field(description="Khía cạnh câu hỏi về luật áp dụng hoặc điều kiện dẫn chiếu.")


_SEED_BODY = f"""
WITH $co_so_ap_dung AS cs, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (l_md:QuyDinh:{TOPIC_LABEL} {{
  id: 'ap_dung_phap_luat_hon_nhan_gia_dinh_viet_nam', topic: '{TOPIC}'
}})
WHERE cs IN ['mac_dinh_phap_luat_viet_nam', 'khong_ro']

OPTIONAL MATCH (l_du:QuyDinh:{TOPIC_LABEL} {{
  id: 'dieu_uoc_quoc_te_uu_tien_khi_co_quy_dinh_khac', topic: '{TOPIC}'
}})
WHERE cs = 'dieu_uoc_quoc_te_co_quy_dinh_khac'

OPTIONAL MATCH (l_vn_dc:DieuKien:{TOPIC_LABEL} {{
  id: 'phap_luat_viet_nam_dan_chieu_phap_luat_nuoc_ngoai', topic: '{TOPIC}'
}})
WHERE cs IN ['phap_luat_viet_nam_dan_chieu', 'tat_ca_truong_hop_dan_chieu']
OPTIONAL MATCH (l_vn_qd:QuyDinh:{TOPIC_LABEL} {{
  id: 'ap_dung_phap_luat_nuoc_ngoai_do_dan_chieu_viet_nam', topic: '{TOPIC}'
}})
WHERE cs IN ['phap_luat_viet_nam_dan_chieu', 'tat_ca_truong_hop_dan_chieu']
OPTIONAL MATCH (l_vn_dk:DieuKien:{TOPIC_LABEL} {{
  id: 'khong_trai_nguyen_tac_co_ban_cua_luat', topic: '{TOPIC}'
}})
WHERE cs IN ['phap_luat_viet_nam_dan_chieu', 'tat_ca_truong_hop_dan_chieu']

OPTIONAL MATCH (l_du_dc:DieuKien:{TOPIC_LABEL} {{
  id: 'dieu_uoc_quoc_te_dan_chieu_phap_luat_nuoc_ngoai', topic: '{TOPIC}'
}})
WHERE cs IN ['dieu_uoc_quoc_te_dan_chieu', 'tat_ca_truong_hop_dan_chieu']
OPTIONAL MATCH (l_du_qd:QuyDinh:{TOPIC_LABEL} {{
  id: 'ap_dung_phap_luat_nuoc_ngoai_do_dan_chieu_dieu_uoc', topic: '{TOPIC}'
}})
WHERE cs IN ['dieu_uoc_quoc_te_dan_chieu', 'tat_ca_truong_hop_dan_chieu']

OPTIONAL MATCH (l_tro_lai:QuyDinh:{TOPIC_LABEL} {{
  id: 'dan_chieu_tro_lai_phap_luat_viet_nam', topic: '{TOPIC}'
}})
WHERE cs = 'phap_luat_nuoc_ngoai_dan_chieu_tro_lai'

OPTIONAL MATCH (l_tq:QuyDinh:{TOPIC_LABEL} {{id: 'nguyen_tac_ap_dung_phap_luat', topic: '{TOPIC}'}})
WHERE cs IN ['khong_ro', 'tong_quat']

WITH wl, cs,
  collect(DISTINCT l_md) + collect(DISTINCT l_du)
    + collect(DISTINCT l_vn_dc) + collect(DISTINCT l_vn_qd) + collect(DISTINCT l_vn_dk)
    + collect(DISTINCT l_du_dc) + collect(DISTINCT l_du_qd)
    + collect(DISTINCT l_tro_lai) + collect(DISTINCT l_tq) AS seed_nodes,
  CASE
    WHEN cs = 'dieu_uoc_quoc_te_co_quy_dinh_khac' THEN
      [x IN collect(DISTINCT l_du) WHERE x IS NOT NULL]
    WHEN cs = 'phap_luat_viet_nam_dan_chieu' THEN
      [x IN collect(DISTINCT l_vn_dc) + collect(DISTINCT l_vn_qd) + collect(DISTINCT l_vn_dk)
       WHERE x IS NOT NULL]
    WHEN cs = 'dieu_uoc_quoc_te_dan_chieu' THEN
      [x IN collect(DISTINCT l_du_dc) + collect(DISTINCT l_du_qd) WHERE x IS NOT NULL]
    WHEN cs = 'tat_ca_truong_hop_dan_chieu' THEN
      [x IN collect(DISTINCT l_vn_dc) + collect(DISTINCT l_vn_qd) + collect(DISTINCT l_vn_dk)
           + collect(DISTINCT l_du_dc) + collect(DISTINCT l_du_qd)
       WHERE x IS NOT NULL]
    WHEN cs = 'phap_luat_nuoc_ngoai_dan_chieu_tro_lai' THEN
      [x IN collect(DISTINCT l_tro_lai) WHERE x IS NOT NULL]
    WHEN cs = 'mac_dinh_phap_luat_viet_nam' THEN
      [x IN collect(DISTINCT l_md) WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT l_tq) + collect(DISTINCT l_md) WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: ApDungPhapLuatParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "co_so_ap_dung": params.co_so_ap_dung,
        "whitelist_dieu_ids": _DIEU_WHITELIST if use_wl else [],
    }


ap_dung_phap_luat_yeu_to_nuoc_ngoai = CypherTemplate(
    name="ap_dung_phap_luat_yeu_to_nuoc_ngoai",
    description=(
        "Dùng cho nguyên tắc xung đột pháp luật chung tại Điều 122: luật Việt Nam mặc định, "
        "ưu tiên điều ước quốc tế, dẫn chiếu áp dụng luật nước ngoài và dẫn chiếu trở lại. "
        "Không dùng chỉ vì câu có 'pháp luật nào' nếu câu đã nêu kết hôn, ly hôn, cấp dưỡng "
        "hoặc tài sản Điều 130. "
        "Ví dụ: Điều ước quốc tế có quy định khác với Luật thì áp dụng thế nào?; "
        "Pháp luật nước ngoài dẫn chiếu trở lại Việt Nam thì xử lý ra sao?"
    ),
    params_schema=ApDungPhapLuatParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
