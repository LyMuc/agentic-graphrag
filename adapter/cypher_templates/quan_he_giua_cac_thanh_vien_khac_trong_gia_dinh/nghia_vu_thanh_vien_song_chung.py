"""Template — nghĩa vụ thành viên sống chung (Đ103 K2)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.quan_he_giua_cac_thanh_vien_khac_trong_gia_dinh._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("loai_nghia_vu_song_chung",)
_DIEU_WHITELIST = ["Luat_HNGD_2014_Dieu_103_Khoan_2"]


class NghiaVuThanhVienSongChungParams(BaseModel):
    loai_nghia_vu_song_chung: Literal[
        "tham_gia_cong_viec_gia_dinh",
        "lao_dong_tao_thu_nhap",
        "dong_gop_cong_suc",
        "dong_gop_tien",
        "dong_gop_tai_san_khac",
        "dong_gop_tong_hop",
        "tong_quat",
    ] = Field(description="loại nghĩa vụ khi sống chung theo Đ103 K2.")
    quan_he_tinh_huong: Literal[
        "di_va_chau",
        "thanh_vien_khac",
        "khong_ro",
    ] = Field(description="quan hệ tình huống — không thay đổi quy tắc Đ103 K2.")
    khia_canh_danh_gia: Literal[
        "co_nghia_vu_khong",
        "pham_vi_nghia_vu",
        "muc_dong_gop",
        "tong_quat",
    ] = Field(description="mức đóng góp / phạm vi nghĩa vụ.")


_SEED_BODY = f"""
WITH $loai_nghia_vu AS ln, $khia_canh AS kc, $seed_muc_dong_gop AS smd, $whitelist_dieu_ids AS wl

MATCH (dk:DieuKien:{TOPIC_LABEL} {{id: 'cac_thanh_vien_dang_song_chung', topic: '{TOPIC}'}})

OPTIONAL MATCH (nv1:NghiaVu:{TOPIC_LABEL} {{id: 'nghia_vu_tham_gia_cong_viec_gia_dinh', topic: '{TOPIC}'}})
WHERE ln IN ['tham_gia_cong_viec_gia_dinh', 'tong_quat']
  OR kc IN ['pham_vi_nghia_vu', 'tong_quat']
OPTIONAL MATCH (nv2:NghiaVu:{TOPIC_LABEL} {{id: 'nghia_vu_lao_dong_tao_thu_nhap', topic: '{TOPIC}'}})
WHERE ln IN ['lao_dong_tao_thu_nhap', 'tong_quat']
  OR kc IN ['pham_vi_nghia_vu', 'tong_quat']
OPTIONAL MATCH (nv3:NghiaVu:{TOPIC_LABEL} {{id: 'nghia_vu_dong_gop_cong_suc', topic: '{TOPIC}'}})
WHERE ln IN ['dong_gop_cong_suc', 'dong_gop_tong_hop', 'tong_quat']
OPTIONAL MATCH (nv4:NghiaVu:{TOPIC_LABEL} {{id: 'nghia_vu_dong_gop_tien', topic: '{TOPIC}'}})
WHERE ln IN ['dong_gop_tien', 'dong_gop_tong_hop', 'tong_quat']
OPTIONAL MATCH (nv5:NghiaVu:{TOPIC_LABEL} {{id: 'nghia_vu_dong_gop_tai_san_khac', topic: '{TOPIC}'}})
WHERE ln IN ['dong_gop_tai_san_khac', 'dong_gop_tong_hop', 'tong_quat']

OPTIONAL MATCH (dk_muc:DieuKien:{TOPIC_LABEL} {{
  id: 'dong_gop_phu_hop_kha_nang_thuc_te', topic: '{TOPIC}'
}})
WHERE smd = true
  OR ln IN ['dong_gop_cong_suc', 'dong_gop_tien', 'dong_gop_tai_san_khac', 'dong_gop_tong_hop']
  OR kc = 'muc_dong_gop'

WITH wl,
  collect(DISTINCT dk) + collect(DISTINCT nv1) + collect(DISTINCT nv2)
    + collect(DISTINCT nv3) + collect(DISTINCT nv4) + collect(DISTINCT nv5)
    + collect(DISTINCT dk_muc) AS seed_nodes,
  [x IN collect(DISTINCT dk) + collect(DISTINCT nv1) + collect(DISTINCT nv2)
       + collect(DISTINCT nv3) + collect(DISTINCT nv4) + collect(DISTINCT nv5)
       + collect(DISTINCT dk_muc)
   WHERE x IS NOT NULL] AS leaf_seed_nodes
"""


def _params_builder(params: NghiaVuThanhVienSongChungParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    seed_muc = params.khia_canh_danh_gia in ("muc_dong_gop", "tong_quat") or params.loai_nghia_vu_song_chung in (
        "dong_gop_cong_suc",
        "dong_gop_tien",
        "dong_gop_tai_san_khac",
        "dong_gop_tong_hop",
    )
    return {
        "loai_nghia_vu": params.loai_nghia_vu_song_chung,
        "khia_canh": params.khia_canh_danh_gia,
        "seed_muc_dong_gop": seed_muc,
        "whitelist_dieu_ids": _DIEU_WHITELIST if use_wl else [],
    }


nghia_vu_thanh_vien_song_chung = CypherTemplate(
    name="nghia_vu_thanh_vien_song_chung",
    description=(
        "Dùng khi câu hỏi có điều kiện các thành viên sống chung và hỏi công việc gia đình, "
        "lao động tạo thu nhập hoặc đóng góp công sức, tiền, tài sản. "
        "Ví dụ: Khi các thành viên gia đình sống chung thì có những nghĩa vụ gì?; "
        "Em đang sống chung với dì ruột, dì yêu cầu đóng góp tiền ăn ở theo khả năng thực tế."
    ),
    params_schema=NghiaVuThanhVienSongChungParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
