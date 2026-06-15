"""Template — định đoạt tài sản con từ 15 đến dưới 18 tuổi (Đ77 k2)."""
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

_ROUTER_FIELDS = ("khia_canh_dinh_doat",)
_DIEU_WHITELIST = ["Luat_HNGD_2014_Dieu_77"]
_THOA_THUAN_LEAF = "dong_y_bang_van_ban_cua_cha_me_hoac_nguoi_giam_ho"


class DinhDoatTaiSanConTuDu15DenDuoi18TuoiParams(BaseModel):
    tuoi_con: int | None = Field(description="Tuổi con từ 15 đến dưới 18 nếu câu nêu rõ.")
    loai_tai_san: Literal[
        "tai_san_thong_thuong",
        "bat_dong_san",
        "dong_san_phai_dang_ky",
        "khong_ro",
    ] = Field(description="bất động sản hoặc động sản phải đăng ký kích hoạt ngoại lệ.")
    hinh_thuc_dinh_doat: Literal[
        "dinh_doat_chung",
        "ban",
        "chuyen_nhuong",
        "dung_de_kinh_doanh",
        "khong_ro",
    ] = Field(description="dùng tài sản kinh doanh -> dung_de_kinh_doanh.")
    khia_canh_dinh_doat: Literal[
        "tu_dinh_doat",
        "co_can_dong_y_bang_van_ban",
        "tong_quat",
    ] = Field(description="hỏi có cần đồng ý bằng văn bản của cha mẹ/người giám hộ.")


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
    params: DinhDoatTaiSanConTuDu15DenDuoi18TuoiParams,
) -> tuple[list[str], list[str]]:
    leaf_ids = ["quyen_dinh_doat_tai_san_con_tu_du_15_den_duoi_18"]
    trace_ids: list[str] = ["con_tu_du_15_den_duoi_18_tuoi"]
    needs_consent = False

    loai = params.loai_tai_san
    hinh_thuc = params.hinh_thuc_dinh_doat
    if loai == "bat_dong_san":
        leaf_ids.extend(["bat_dong_san", "tai_san_la_bat_dong_san"])
        needs_consent = True
    elif loai == "dong_san_phai_dang_ky":
        leaf_ids.extend(["dong_san_phai_dang_ky", "tai_san_la_dong_san_phai_dang_ky"])
        needs_consent = True
    if hinh_thuc == "dung_de_kinh_doanh":
        leaf_ids.append("dung_tai_san_de_kinh_doanh")
        trace_ids.append("giao_dich_dung_tai_san_de_kinh_doanh")
        needs_consent = True
    if params.khia_canh_dinh_doat == "co_can_dong_y_bang_van_ban" and needs_consent:
        leaf_ids.append(_THOA_THUAN_LEAF)
    elif needs_consent:
        leaf_ids.append(_THOA_THUAN_LEAF)

    return leaf_ids, trace_ids


def _params_builder(params: DinhDoatTaiSanConTuDu15DenDuoi18TuoiParams) -> dict[str, Any]:
    leaf_ids, trace_ids = _resolve_ids(params)
    use_wl = not leaf_ids and should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "leaf_ids": leaf_ids,
        "trace_ids": trace_ids,
        "whitelist_dieu_ids": _DIEU_WHITELIST if use_wl else [],
    }


dinh_doat_tai_san_con_tu_du_15_den_duoi_18_tuoi = CypherTemplate(
    name="dinh_doat_tai_san_con_tu_du_15_den_duoi_18_tuoi",
    description=(
        "Trả lời quyền định đoạt của con từ đủ 15 đến dưới 18 tuổi và ba ngoại lệ phải có "
        "đồng ý bằng văn bản: bất động sản, động sản đăng ký, dùng tài sản kinh doanh (Đ77 k2). "
        "Ví dụ: Con 16 tuổi muốn chuyển nhượng đất có cần cha mẹ đồng ý bằng văn bản không?; "
        "Con 17 tuổi dùng tiền tiết kiệm mở quán ăn có cần cha mẹ đồng ý bằng văn bản không?"
    ),
    params_schema=DinhDoatTaiSanConTuDu15DenDuoi18TuoiParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
