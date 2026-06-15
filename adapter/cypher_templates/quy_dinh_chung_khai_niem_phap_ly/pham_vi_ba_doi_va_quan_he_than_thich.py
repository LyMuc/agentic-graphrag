"""Template — phạm vi ba đời và quan hệ thân thích (Đ3 K17-18, Đ5 K2 điểm d)."""
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

_ROUTER_FIELDS = ("loai_quan_he", "khia_canh_ba_doi")
_DIEU_WHITELIST = ["Luat_HNGD_2014_Dieu_3", "Luat_HNGD_2014_Dieu_5"]

_LOAI_QUAN_HE_MAP: dict[str, str] = {
    "cung_dong_mau_truc_he": "khai_niem_cung_dong_mau_ve_truc_he",
    "ho_trong_pham_vi_ba_doi": "khai_niem_ho_trong_pham_vi_ba_doi",
    "cha_me_doi_thu_nhat": "cha_me_la_doi_thu_nhat",
    "anh_chi_em_doi_thu_hai": "anh_chi_em_la_doi_thu_hai",
    "anh_chi_em_ho_doi_thu_ba": "anh_chi_em_ho_la_doi_thu_ba",
    "quan_he_nuoi_duong_thong_gia_bi_cam": "hanh_vi_cam_quan_he_than_thich",
}


class PhamViBaDoiVaQuanHeThanThichParams(BaseModel):
    loai_quan_he: Literal[
        "cung_dong_mau_truc_he",
        "ho_trong_pham_vi_ba_doi",
        "cha_me_doi_thu_nhat",
        "anh_chi_em_doi_thu_hai",
        "anh_chi_em_ho_doi_thu_ba",
        "quan_he_nuoi_duong_thong_gia_bi_cam",
        "khong_ro",
    ] = Field(description="Loại quan hệ huyết thống hoặc họ ba đời.")
    khia_canh_ba_doi: Literal[
        "so_doi_bi_cam",
        "liet_ke_nguoi_trong_ba_doi",
        "cach_tinh_ba_doi",
        "co_bi_cam_ket_hon",
        "tong_quat",
    ] = Field(description="Hỏi số đời cấm, liệt kê thành phần hoặc đánh giá cấm kết hôn.")


_SEED_BODY = f"""
WITH $lr AS lr, $kc AS kc, $sid AS sid, $expand_ba_doi AS expand_ba_doi,
     $seed_cam AS seed_cam, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (qh:QuanHe:{TOPIC_LABEL} {{id: sid, topic: '{TOPIC}'}})
WHERE sid <> '' AND sid <> 'hanh_vi_cam_quan_he_than_thich'

OPTIONAL MATCH (qh_ba:QuanHe:{TOPIC_LABEL} {{
  id: 'khai_niem_ho_trong_pham_vi_ba_doi', topic: '{TOPIC}'
}})
WHERE expand_ba_doi = true OR lr = 'ho_trong_pham_vi_ba_doi'

OPTIONAL MATCH (qh_ba)-[:BAO_GOM]->(doi:QuanHe:{TOPIC_LABEL})
WHERE expand_ba_doi = true AND doi.topic = '{TOPIC}'

OPTIONAL MATCH (qh_truc:QuanHe:{TOPIC_LABEL} {{
  id: 'khai_niem_cung_dong_mau_ve_truc_he', topic: '{TOPIC}'
}})
WHERE lr = 'cung_dong_mau_truc_he' OR kc = 'tong_quat'

OPTIONAL MATCH (hv_cam:HanhVi:{TOPIC_LABEL} {{
  id: 'hanh_vi_cam_quan_he_than_thich', topic: '{TOPIC}'
}})
WHERE seed_cam = true OR sid = 'hanh_vi_cam_quan_he_than_thich'

WITH wl, kc, expand_ba_doi, sid, seed_cam,
  collect(DISTINCT qh) + collect(DISTINCT qh_ba) + collect(DISTINCT doi)
    + collect(DISTINCT qh_truc) + collect(DISTINCT hv_cam)
    AS seed_nodes,
  CASE
    WHEN expand_ba_doi = true THEN
      [x IN collect(DISTINCT doi) + collect(DISTINCT qh_ba) WHERE x IS NOT NULL]
    WHEN sid = 'hanh_vi_cam_quan_he_than_thich' THEN
      [x IN collect(DISTINCT hv_cam) WHERE x IS NOT NULL]
    WHEN seed_cam = true THEN
      [x IN collect(DISTINCT qh) + collect(DISTINCT qh_truc) + collect(DISTINCT hv_cam)
       WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT qh) + collect(DISTINCT qh_truc) WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: PhamViBaDoiVaQuanHeThanThichParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    lr = params.loai_quan_he
    kc = params.khia_canh_ba_doi
    sid = _LOAI_QUAN_HE_MAP.get(lr, "")
    expand_ba_doi = lr == "ho_trong_pham_vi_ba_doi" and kc in (
        "liet_ke_nguoi_trong_ba_doi",
        "cach_tinh_ba_doi",
        "tong_quat",
    )
    seed_cam = kc in ("so_doi_bi_cam", "co_bi_cam_ket_hon") or lr == "cung_dong_mau_truc_he"
    if lr == "quan_he_nuoi_duong_thong_gia_bi_cam":
        sid = "hanh_vi_cam_quan_he_than_thich"
        expand_ba_doi = False
        seed_cam = False
    return {
        "lr": lr,
        "kc": kc,
        "sid": sid,
        "expand_ba_doi": expand_ba_doi,
        "seed_cam": seed_cam,
        "whitelist_dieu_ids": _DIEU_WHITELIST if use_wl else [],
    }


pham_vi_ba_doi_va_quan_he_than_thich = CypherTemplate(
    name="pham_vi_ba_doi_va_quan_he_than_thich",
    description=(
        "Truy xuất định nghĩa cùng dòng máu về trực hệ, người có họ trong phạm vi ba đời và "
        "cách xác định đời thứ nhất, thứ hai, thứ ba tại khoản 17-18 Điều 3. Khi hỏi cấm kết hôn "
        "seed thêm điểm d khoản 2 Điều 5. "
        "Ví dụ: Pháp luật nghiêm cấm kết hôn giữa những người có họ trong phạm vi mấy đời?; "
        "Những người có họ trong phạm vi ba đời gồm những ai?"
    ),
    params_schema=PhamViBaDoiVaQuanHeThanThichParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
