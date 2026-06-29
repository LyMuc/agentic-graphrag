"""Template — ngưỡng tuổi và đánh giá đủ tuổi kết hôn (Đ8 K1 điểm a)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from server.infrastructure.neo4j.cypher_templates import CypherTemplate
from server.infrastructure.neo4j.cypher_templates.dieu_kien_ket_hon._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("khia_canh_tuoi",)
_DIEU_WHITELIST = ["Luat_HNGD_2014_Dieu_5", "Luat_HNGD_2014_Dieu_8"]


class DoTuoiKetHonParams(BaseModel):
    gioi_tinh_nguoi_can_xet: Literal["nam", "nu", "ca_hai", "khong_ro"] = Field(
        description=(
            "nam/con trai/chồng -> nam; nữ/con gái/vợ -> nu; "
            "nam nữ đều/hai bên -> ca_hai."
        )
    )
    dang_du_lieu_tuoi: Literal[
        "tuoi_hien_tai",
        "nam_sinh_va_nam_xet",
        "ca_hai_cung_tuoi",
        "khong_ro",
    ] = Field(
        description=(
            "có 18 tuổi/20 tuổi -> tuoi_hien_tai; "
            "sinh năm... năm... -> nam_sinh_va_nam_xet; "
            "nam nữ đều 18 -> ca_hai_cung_tuoi."
        )
    )
    khia_canh_tuoi: Literal[
        "nguong_tuoi",
        "da_du_tuoi",
        "nam_sinh_du_dieu_kien",
        "tong_quat",
    ] = Field(
        description=(
            "bao nhiêu tuổi -> nguong_tuoi; "
            "đã đủ chưa/có được không -> da_du_tuoi; "
            "sinh năm bao nhiêu -> nam_sinh_du_dieu_kien."
        )
    )
    tuoi_nam: int | None = Field(default=None, description="Tuổi của nam nếu câu nêu.")
    tuoi_nu: int | None = Field(default=None, description="Tuổi của nữ nếu câu nêu.")
    nam_sinh: int | None = Field(default=None, description="Năm sinh được nêu.")
    nam_xet: int | None = Field(
        default=None,
        description="Năm dự định kết hôn hoặc năm cần đánh giá.",
    )


_SEED_BODY = f"""
WITH $gt AS gt, $kc AS kc, $seed_tao_hon AS seed_tao_hon,
     $whitelist_dieu_ids AS wl

OPTIONAL MATCH (dk_nam:DieuKien:{TOPIC_LABEL} {{id: 'nam_tu_du_20_tuoi', topic: '{TOPIC}'}})
WHERE gt IN ['nam', 'ca_hai', 'khong_ro']

OPTIONAL MATCH (dk_nu:DieuKien:{TOPIC_LABEL} {{id: 'nu_tu_du_18_tuoi', topic: '{TOPIC}'}})
WHERE gt IN ['nu', 'ca_hai', 'khong_ro']

OPTIONAL MATCH (hv_tao:HanhVi:{TOPIC_LABEL} {{id: 'tao_hon', topic: '{TOPIC}'}})
WHERE seed_tao_hon = true

WITH wl, kc, gt,
  [x IN collect(DISTINCT dk_nam) + collect(DISTINCT dk_nu) + collect(DISTINCT hv_tao)
   WHERE x IS NOT NULL] AS seed_nodes,
  CASE gt
    WHEN 'nam' THEN
      [x IN collect(DISTINCT dk_nam) + collect(DISTINCT hv_tao) WHERE x IS NOT NULL]
    WHEN 'nu' THEN
      [x IN collect(DISTINCT dk_nu) + collect(DISTINCT hv_tao) WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT dk_nam) + collect(DISTINCT dk_nu) + collect(DISTINCT hv_tao)
       WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _maybe_seed_tao_hon(params: DoTuoiKetHonParams) -> bool:
    if params.khia_canh_tuoi not in ("da_du_tuoi", "tong_quat"):
        return False
    if params.tuoi_nam is not None and params.tuoi_nam < 20:
        return True
    if params.tuoi_nu is not None and params.tuoi_nu < 18:
        return True
    if (
        params.dang_du_lieu_tuoi == "ca_hai_cung_tuoi"
        and params.tuoi_nam == 18
        and params.tuoi_nu == 18
    ):
        return True
    return False


def _params_builder(params: DoTuoiKetHonParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "gt": params.gioi_tinh_nguoi_can_xet,
        "kc": params.khia_canh_tuoi,
        "seed_tao_hon": _maybe_seed_tao_hon(params),
        "whitelist_dieu_ids": _DIEU_WHITELIST if use_wl else [],
    }


do_tuoi_ket_hon = CypherTemplate(
    name="do_tuoi_ket_hon",
    description=(
        "Trả lời ngưỡng tuổi kết hôn và đánh giá tuổi theo giới tính: nam từ đủ 20 tuổi, "
        "nữ từ đủ 18 tuổi. Template nhận tuổi hoặc năm sinh/năm xét, nhưng phải cảnh báo "
        "khi thiếu ngày tháng sinh mà câu hỏi yêu cầu kết luận tại một thời điểm trong năm. "
        "Ví dụ: Nam sinh năm bao nhiêu thì đủ tuổi kết hôn năm 2026?; "
        "Nam nữ đều 18 tuổi có được kết hôn với nhau?"
    ),
    params_schema=DoTuoiKetHonParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
