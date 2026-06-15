"""Template — bảo vệ chế độ và hành vi bị cấm (Đ5)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.quy_dinh_chung_khai_niem_phap_ly._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("nhom_hanh_vi", "khia_canh_bao_ve_cam")
_DIEU_WHITELIST = ["Luat_HNGD_2014_Dieu_5"]

_NHOM_HANH_VI_MAP: dict[str, str] = {
    "ket_hon_ly_hon_gia_tao": "hanh_vi_cam_ket_hon_ly_hon_gia_tao",
    "tao_hon_cuong_ep_lua_doi_can_tro_ket_hon": "hanh_vi_cam_tao_hon_cuong_ep_lua_doi_can_tro_ket_hon",
    "vi_pham_mot_vo_mot_chong": "hanh_vi_cam_vi_pham_mot_vo_mot_chong",
    "quan_he_than_thich_bi_cam": "hanh_vi_cam_quan_he_than_thich",
    "yeu_sach_cua_cai": "hanh_vi_cam_yeu_sach_cua_cai",
    "cuong_ep_lua_doi_can_tro_ly_hon": "hanh_vi_cam_cuong_ep_lua_doi_can_tro_ly_hon",
    "sinh_san_thuong_mai_lua_chon_gioi_tinh": "hanh_vi_cam_sinh_san_thuong_mai_lua_chon_gioi_tinh",
    "bao_luc_gia_dinh": "hanh_vi_cam_bao_luc_gia_dinh",
    "loi_dung_quyen_hngd_de_truc_loi": "hanh_vi_cam_loi_dung_quyen_hngd_de_truc_loi",
}


class BaoVeCheDoVaHanhViBiCamParams(BaseModel):
    nhom_hanh_vi: Literal[
        "tat_ca",
        "ket_hon_ly_hon_gia_tao",
        "tao_hon_cuong_ep_lua_doi_can_tro_ket_hon",
        "vi_pham_mot_vo_mot_chong",
        "quan_he_than_thich_bi_cam",
        "yeu_sach_cua_cai",
        "cuong_ep_lua_doi_can_tro_ly_hon",
        "sinh_san_thuong_mai_lua_chon_gioi_tinh",
        "bao_luc_gia_dinh",
        "loi_dung_quyen_hngd_de_truc_loi",
        "khong_ro",
    ] = Field(description="Nhóm hành vi bị cấm tại khoản 2 Điều 5.")
    dang_quan_he_thuc_te: Literal[
        "ket_hon",
        "chung_song_nhu_vo_chong",
        "qua_lai_tinh_cam",
        "khong_ro",
    ] = Field(description="Mức độ quan hệ thực tế nếu câu hỏi mô tả.")
    tinh_trang_hon_nhan: Literal[
        "dang_co_vo_chong",
        "ly_than_chua_ly_hon",
        "da_ly_hon",
        "chua_co_vo_chong",
        "khong_ro",
    ] = Field(description="Tình trạng hôn nhân liên quan.")
    khia_canh_bao_ve_cam: Literal[
        "liet_ke",
        "dinh_nghia_hanh_vi",
        "co_vi_pham",
        "xu_ly_bao_ve",
        "tong_quat",
    ] = Field(description="Liệt kê, định nghĩa, đánh giá vi phạm hoặc xử lý/bảo vệ.")


_SEED_BODY = f"""
WITH $nh AS nh, $dqt AS dqt, $tthn AS tthn, $kc AS kc,
     $expand_cam AS expand_cam, $hv_id AS hv_id,
     $seed_ly_than AS seed_ly_than, $seed_qua_lai AS seed_qua_lai,
     $seed_chung_song AS seed_chung_song, $seed_xu_ly AS seed_xu_ly,
     $whitelist_dieu_ids AS wl

OPTIONAL MATCH (root_cam:QuyDinh:{TOPIC_LABEL} {{
  id: 'cac_hanh_vi_bi_cam_trong_hngd', topic: '{TOPIC}'
}})
WHERE expand_cam = true

OPTIONAL MATCH (root_cam)-[:BAO_GOM]->(hv:HanhVi:{TOPIC_LABEL})
WHERE expand_cam = true AND hv.topic = '{TOPIC}'

OPTIONAL MATCH (hv_one:HanhVi:{TOPIC_LABEL} {{id: hv_id, topic: '{TOPIC}'}})
WHERE hv_id <> '' AND expand_cam = false

OPTIONAL MATCH (cs:HanhVi:{TOPIC_LABEL} {{
  id: 'khai_niem_chung_song_nhu_vo_chong', topic: '{TOPIC}'
}})
WHERE seed_chung_song = true

OPTIONAL MATCH (cs2:HanhVi:{TOPIC_LABEL} {{
  id: 'chung_song_voi_nguoi_khac_khi_dang_co_vo_chong', topic: '{TOPIC}'
}})
WHERE seed_chung_song = true

OPTIONAL MATCH (tk:QuanHe:{TOPIC_LABEL} {{
  id: 'khai_niem_thoi_ky_hon_nhan', topic: '{TOPIC}'
}})
WHERE seed_ly_than = true
OPTIONAL MATCH (lh:HanhVi:{TOPIC_LABEL} {{id: 'khai_niem_ly_hon', topic: '{TOPIC}'}})
WHERE seed_ly_than = true
OPTIONAL MATCH (lt:QuyDinh:{TOPIC_LABEL} {{
  id: 'ly_than_khong_tu_cham_dut_thoi_ky_hon_nhan', topic: '{TOPIC}'
}})
WHERE seed_ly_than = true

OPTIONAL MATCH (ql:DieuKien:{TOPIC_LABEL} {{
  id: 'qua_lai_tinh_cam_can_xac_minh_muc_do', topic: '{TOPIC}'
}})
WHERE seed_qua_lai = true

OPTIONAL MATCH (bv:HauQua:{TOPIC_LABEL})
WHERE seed_xu_ly = true
  AND bv.id IN [
    'quan_he_hngd_hop_phap_duoc_ton_trong_bao_ve',
    'xu_ly_nghiem_hanh_vi_vi_pham_hngd',
    'quyen_yeu_cau_ngan_chan_xu_ly_vi_pham',
    'ton_trong_bao_ve_danh_du_nhan_pham_rieng_tu'
  ]
  AND bv.topic = '{TOPIC}'

WITH wl, kc,
  collect(DISTINCT root_cam) + collect(DISTINCT hv) + collect(DISTINCT hv_one)
    + collect(DISTINCT cs) + collect(DISTINCT cs2)
    + collect(DISTINCT tk) + collect(DISTINCT lh) + collect(DISTINCT lt)
    + collect(DISTINCT ql) + collect(DISTINCT bv)
    AS seed_nodes,
  [x IN collect(DISTINCT hv) + collect(DISTINCT hv_one)
       + collect(DISTINCT cs) + collect(DISTINCT cs2)
       + collect(DISTINCT tk) + collect(DISTINCT lh) + collect(DISTINCT lt)
       + collect(DISTINCT ql) + collect(DISTINCT bv)
   WHERE x IS NOT NULL] AS leaf_seed_nodes
"""


def _params_builder(params: BaoVeCheDoVaHanhViBiCamParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    nh = params.nhom_hanh_vi
    dqt = params.dang_quan_he_thuc_te
    tthn = params.tinh_trang_hon_nhan
    kc = params.khia_canh_bao_ve_cam
    expand_cam = nh in ("tat_ca", "khong_ro") and kc in ("liet_ke", "tong_quat")
    hv_id = "" if expand_cam else _NHOM_HANH_VI_MAP.get(nh, "")
    seed_chung_song = nh == "vi_pham_mot_vo_mot_chong" and dqt == "chung_song_nhu_vo_chong"
    seed_ly_than = tthn == "ly_than_chua_ly_hon"
    seed_qua_lai = dqt == "qua_lai_tinh_cam"
    seed_xu_ly = kc == "xu_ly_bao_ve"
    return {
        "nh": nh,
        "dqt": dqt,
        "tthn": tthn,
        "kc": kc,
        "expand_cam": expand_cam,
        "hv_id": hv_id,
        "seed_ly_than": seed_ly_than,
        "seed_qua_lai": seed_qua_lai,
        "seed_chung_song": seed_chung_song,
        "seed_xu_ly": seed_xu_ly,
        "whitelist_dieu_ids": _DIEU_WHITELIST if use_wl else [],
    }


bao_ve_che_do_va_hanh_vi_bi_cam = CypherTemplate(
    name="bao_ve_che_do_va_hanh_vi_bi_cam",
    description=(
        "Truy xuất nguyên tắc bảo vệ, danh sách hành vi bị cấm và hậu quả xử lý tại Điều 5. "
        "Xử lý riêng vi phạm một vợ một chồng, chung sống như vợ chồng và tình huống ly thân. "
        "Cụm qua lại không đủ để tự kết luận vi phạm. "
        "Ví dụ: Ngoại tình bằng việc sống chung được hiểu thế nào?; "
        "Các hành vi bị cấm trong lĩnh vực hôn nhân và gia đình?; "
        "Qua lại với người khác trong thời gian ly thân có vi phạm luật hôn nhân không?"
    ),
    params_schema=BaoVeCheDoVaHanhViBiCamParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
