"""Template — quyền, nghĩa vụ trong quan hệ nuôi con nuôi (Đ78, Đ68 k3)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from server.infrastructure.neo4j.cypher_templates import CypherTemplate
from server.infrastructure.neo4j.cypher_templates.quyen_nghia_vu_cha_me_con._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("khia_canh_nuoi_con_nuoi",)
_DIEU_WHITELIST = ["Luat_HNGD_2014_Dieu_68", "Luat_HNGD_2014_Dieu_78"]


class QuyenNghiaVuChaMeNuoiConNuoiParams(BaseModel):
    khia_canh_nuoi_con_nuoi: Literal[
        "quyen_nghia_vu_chung",
        "thoi_diem_phat_sinh",
        "thoi_diem_cham_dut",
        "quyen_nghia_vu_cha_me_de",
        "khoi_phuc_quyen_nghia_vu_cha_me_de",
        "chi_dinh_nguoi_giam_ho",
        "tong_quat",
    ] = Field(description="xác lập/kể từ thời điểm nào -> thoi_diem_phat_sinh; chấm dứt -> thoi_diem_cham_dut.")
    trang_thai_quan_he_nuoi_con_nuoi: Literal[
        "chua_xac_lap",
        "da_xac_lap",
        "da_cham_dut",
        "khong_ro",
    ] = Field(description="Map trạng thái quan hệ nuôi con nuôi.")
    chu_the_quan_he_nuoi_con_nuoi: Literal[
        "cha_me_nuoi_va_con_nuoi",
        "cha_me_de_va_con_de",
        "tat_ca",
        "khong_ro",
    ] = Field(description="cha nuôi/mẹ nuôi -> cha_me_nuoi_va_con_nuoi.")


_SEED_BODY = f"""
WITH $khia AS khia, $seed_giam_ho AS seed_giam_ho, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (leaf_d68:QuyDinh:{TOPIC_LABEL} {{
  id: 'quan_he_cha_me_nuoi_con_nuoi_co_quyen_nghia_vu_cha_me_con', topic: '{TOPIC}'
}})
WHERE khia IN ['quyen_nghia_vu_chung', 'tong_quat']

OPTIONAL MATCH (dk_ps:DieuKien:{TOPIC_LABEL} {{
  id: 'quan_he_nuoi_con_nuoi_duoc_xac_lap', topic: '{TOPIC}'
}})
WHERE khia IN ['quyen_nghia_vu_chung', 'thoi_diem_phat_sinh', 'tong_quat']

OPTIONAL MATCH (hq_ps:HauQua:{TOPIC_LABEL} {{
  id: 'quyen_nghia_vu_cha_me_nuoi_con_nuoi_phat_sinh', topic: '{TOPIC}'
}})
WHERE khia IN ['quyen_nghia_vu_chung', 'thoi_diem_phat_sinh', 'tong_quat']

OPTIONAL MATCH (dk_cd:DieuKien:{TOPIC_LABEL} {{
  id: 'quyet_dinh_cham_dut_nuoi_con_nuoi_co_hieu_luc', topic: '{TOPIC}'
}})
WHERE khia = 'thoi_diem_cham_dut'

OPTIONAL MATCH (hq_cd:HauQua:{TOPIC_LABEL} {{
  id: 'quyen_nghia_vu_cha_me_nuoi_con_nuoi_cham_dut', topic: '{TOPIC}'
}})
WHERE khia = 'thoi_diem_cham_dut'

OPTIONAL MATCH (qd_de:QuyDinh:{TOPIC_LABEL} {{
  id: 'quyen_nghia_vu_cha_me_de_con_da_cho_lam_con_nuoi', topic: '{TOPIC}'
}})
WHERE khia = 'quyen_nghia_vu_cha_me_de'

OPTIONAL MATCH (dk_kp:DieuKien:{TOPIC_LABEL} {{
  id: 'quan_he_nuoi_con_nuoi_cham_dut', topic: '{TOPIC}'
}})
WHERE khia IN ['khoi_phuc_quyen_nghia_vu_cha_me_de', 'thoi_diem_cham_dut']

OPTIONAL MATCH (hq_kp:HauQua:{TOPIC_LABEL} {{
  id: 'quyen_nghia_vu_cha_me_de_con_de_duoc_khoi_phuc', topic: '{TOPIC}'
}})
WHERE khia = 'khoi_phuc_quyen_nghia_vu_cha_me_de'

OPTIONAL MATCH (hq_gh:HauQua:{TOPIC_LABEL} {{
  id: 'toa_an_chi_dinh_nguoi_giam_ho_khi_can', topic: '{TOPIC}'
}})
WHERE seed_giam_ho = true

WITH wl, khia,
  collect(DISTINCT leaf_d68) + collect(DISTINCT dk_ps) + collect(DISTINCT hq_ps)
    + collect(DISTINCT dk_cd) + collect(DISTINCT hq_cd)
    + collect(DISTINCT qd_de) + collect(DISTINCT dk_kp) + collect(DISTINCT hq_kp)
    + collect(DISTINCT hq_gh)
    AS seed_nodes,
  [x IN collect(DISTINCT leaf_d68) + collect(DISTINCT dk_ps) + collect(DISTINCT hq_ps)
        + collect(DISTINCT dk_cd) + collect(DISTINCT hq_cd)
        + collect(DISTINCT qd_de) + collect(DISTINCT dk_kp) + collect(DISTINCT hq_kp)
        + collect(DISTINCT hq_gh)
   WHERE x IS NOT NULL] AS leaf_seed_nodes
"""


def _params_builder(params: QuyenNghiaVuChaMeNuoiConNuoiParams) -> dict[str, Any]:
    khia = params.khia_canh_nuoi_con_nuoi
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "khia": khia,
        "seed_giam_ho": khia == "chi_dinh_nguoi_giam_ho",
        "whitelist_dieu_ids": _DIEU_WHITELIST if use_wl else [],
    }


quyen_nghia_vu_cha_me_nuoi_con_nuoi = CypherTemplate(
    name="quyen_nghia_vu_cha_me_nuoi_con_nuoi",
    description=(
        "Trả lời Điều 78 và Điều 68 khoản 3 về quyền, nghĩa vụ giữa cha mẹ nuôi, con nuôi "
        "và quan hệ với cha mẹ đẻ. Dùng khi hỏi thời điểm phát sinh quyền nghĩa vụ, "
        "nền tảng quyền nghĩa vụ cha mẹ-con trong quan hệ nuôi con nuôi, "
        "chấm dứt nuôi con nuôi hoặc khôi phục quyền cha mẹ đẻ."
    ),
    params_schema=QuyenNghiaVuChaMeNuoiConNuoiParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
