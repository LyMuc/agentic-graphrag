"""Template — cha mẹ quản lý tài sản con dưới 15/mất năng lực (Đ76 k2)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.tai_san_rieng_cua_con._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("khia_canh_quan_ly",)
_DIEU_WHITELIST = ["Luat_HNGD_2014_Dieu_76"]


class QuanLyTaiSanConDuoi15HoacMatNangLucParams(BaseModel):
    tinh_trang_con: Literal[
        "duoi_15_tuoi",
        "mat_nang_luc_hanh_vi_dan_su",
        "khoi_phuc_nang_luc_hanh_vi_dan_su_day_du",
        "khong_ro",
    ] = Field(description="dưới 15 tuổi hoặc mất năng lực hành vi dân sự.")
    tuoi_con: int | None = Field(description="Tuổi con nếu câu hỏi nêu rõ.")
    khia_canh_quan_ly: Literal[
        "ai_quan_ly",
        "uy_quyen_nguoi_khac",
        "giao_lai_khi_nao",
        "giao_lai_sau_khoi_phuc",
        "thoa_thuan_khac",
        "pham_vi_quan_ly",
        "tong_quat",
    ] = Field(description="ai quản lý, ủy quyền, giao lại tài sản, thỏa thuận khác.")
    loai_tai_san: Literal[
        "tai_san_rieng_cua_con",
        "bat_dong_san",
        "dong_san_phai_dang_ky",
        "khong_ro",
    ] = Field(description="loại tài sản trong câu hỏi quản lý (không chuyển sang định đoạt Đ77).")


_SEED_BODY = f"""
WITH $leaf_ids AS leaf_ids, $trace_ids AS trace_ids, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (leaf)
WHERE leaf.id IN leaf_ids AND leaf.topic = '{TOPIC}' AND '{TOPIC_LABEL}' IN labels(leaf)

OPTIONAL MATCH (trace)
WHERE trace.id IN trace_ids AND trace.topic = '{TOPIC}' AND '{TOPIC_LABEL}' IN labels(trace)

WITH wl,
  collect(DISTINCT leaf) + collect(DISTINCT trace) AS seed_nodes,
  [x IN collect(DISTINCT leaf) WHERE x IS NOT NULL] AS leaf_seed_nodes
"""


def _resolve_ids(
    params: QuanLyTaiSanConDuoi15HoacMatNangLucParams,
) -> tuple[list[str], list[str]]:
    tt = params.tinh_trang_con
    kc = params.khia_canh_quan_ly
    leaf_ids: list[str] = []
    trace_ids: list[str] = []

    if kc == "uy_quyen_nguoi_khac":
        leaf_ids.append("uy_quyen_nguoi_khac_quan_ly_tai_san")
    elif kc in ("giao_lai_khi_nao", "giao_lai_sau_khoi_phuc"):
        leaf_ids.append("giao_lai_tai_san_cho_con")
        if kc == "giao_lai_sau_khoi_phuc" or tt == "khoi_phuc_nang_luc_hanh_vi_dan_su_day_du":
            trace_ids.append("con_khoi_phuc_nang_luc_hanh_vi_dan_su_day_du")
    elif kc == "thoa_thuan_khac":
        leaf_ids.append("giao_lai_tai_san_cho_con")
        trace_ids.append("thoa_thuan_khac_ve_thoi_diem_giao_lai_tai_san")
    elif tt == "duoi_15_tuoi" or kc in ("ai_quan_ly", "pham_vi_quan_ly", "tong_quat"):
        if tt != "mat_nang_luc_hanh_vi_dan_su":
            leaf_ids.append("cha_me_quan_ly_tai_san_con_duoi_15")
    elif tt == "mat_nang_luc_hanh_vi_dan_su":
        leaf_ids.append("cha_me_quan_ly_tai_san_con_mat_nang_luc")

    return leaf_ids, trace_ids


def _params_builder(params: QuanLyTaiSanConDuoi15HoacMatNangLucParams) -> dict[str, Any]:
    leaf_ids, trace_ids = _resolve_ids(params)
    use_wl = not leaf_ids and should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "leaf_ids": leaf_ids,
        "trace_ids": trace_ids,
        "whitelist_dieu_ids": _DIEU_WHITELIST if use_wl else [],
    }


quan_ly_tai_san_con_duoi_15_hoac_mat_nang_luc = CypherTemplate(
    name="quan_ly_tai_san_con_duoi_15_hoac_mat_nang_luc",
    description=(
        "Xử lý cha mẹ quản lý tài sản con dưới 15 tuổi hoặc mất năng lực, ủy quyền người khác, "
        "giao lại tài sản và thỏa thuận khác theo khoản 2 Điều 76. "
        "Ví dụ: Ai quản lý tài sản riêng của con dưới 15 tuổi?; "
        "Con khôi phục năng lực hành vi dân sự thì tài sản do cha mẹ quản lý có được giao lại không?"
    ),
    params_schema=QuanLyTaiSanConDuoi15HoacMatNangLucParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
