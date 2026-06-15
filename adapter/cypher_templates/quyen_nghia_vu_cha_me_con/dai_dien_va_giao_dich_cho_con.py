"""Template — đại diện và giao dịch cho con (Đ73)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.quyen_nghia_vu_cha_me_con._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

_ROUTER_FIELDS = ("loai_van_de_dai_dien",)
_DIEU_WHITELIST = ["Luat_HNGD_2014_Dieu_73"]


class DaiDienVaGiaoDichChoConParams(BaseModel):
    loai_van_de_dai_dien: Literal[
        "nguoi_dai_dien_theo_phap_luat",
        "giao_dich_nhu_cau_thiet_yeu",
        "giao_dich_tai_san_quan_trong",
        "trach_nhiem_lien_doi",
        "tong_quat",
    ] = Field(
        description=(
            "ai đại diện -> nguoi_dai_dien_theo_phap_luat; "
            "đồ thiết yếu -> giao_dich_nhu_cau_thiet_yeu; "
            "bán nhà/tài sản đăng ký -> giao_dich_tai_san_quan_trong."
        )
    )
    loai_tai_san_giao_dich: Literal[
        "nhu_cau_thiet_yeu",
        "bat_dong_san",
        "dong_san_dang_ky",
        "tai_san_dua_vao_kinh_doanh",
        "khac",
        "khong_ro",
    ] = Field(description="nhà/đất -> bat_dong_san; đồ thiết yếu -> nhu_cau_thiet_yeu.")
    chu_the_thuc_hien: Literal["cha", "me", "ca_cha_va_me", "khong_ro"] = Field(
        description="mẹ một mình -> me; cả hai cha mẹ -> ca_cha_va_me."
    )
    tinh_trang_dai_dien_khac: Literal[
        "co_nguoi_giam_ho_khac",
        "co_nguoi_dai_dien_khac",
        "khong_co",
        "khong_ro",
    ] = Field(description="Ngoại lệ khoản 1 khi có giám hộ/đại diện khác.")


_SEED_BODY = f"""
WITH $loai AS loai, $seed_ngoai_le AS seed_ngoai_le, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (leaf_dd:Quyen:{TOPIC_LABEL} {{
  id: 'cha_me_dai_dien_theo_phap_luat_cho_con', topic: '{TOPIC}'
}})
WHERE loai IN ['nguoi_dai_dien_theo_phap_luat', 'tong_quat']

OPTIONAL MATCH (dk:DieuKien:{TOPIC_LABEL} {{
  id: 'ngoai_le_co_nguoi_giam_ho_hoac_dai_dien_khac', topic: '{TOPIC}'
}})
WHERE seed_ngoai_le = true

OPTIONAL MATCH (hv_ty:HanhVi:{TOPIC_LABEL} {{
  id: 'giao_dich_nhu_cau_thiet_yeu_cua_con', topic: '{TOPIC}'
}})
WHERE loai = 'giao_dich_nhu_cau_thiet_yeu'

OPTIONAL MATCH (q_ty:Quyen:{TOPIC_LABEL} {{
  id: 'cha_hoac_me_tu_minh_thuc_hien_giao_dich_thiet_yeu', topic: '{TOPIC}'
}})
WHERE loai = 'giao_dich_nhu_cau_thiet_yeu'

OPTIONAL MATCH (nv_ld:NghiaVu:{TOPIC_LABEL} {{
  id: 'cha_me_chiu_trach_nhiem_lien_doi_giao_dich_tai_san_cua_con', topic: '{TOPIC}'
}})
WHERE loai IN ['giao_dich_nhu_cau_thiet_yeu', 'giao_dich_tai_san_quan_trong', 'trach_nhiem_lien_doi']

OPTIONAL MATCH (hv_ts:HanhVi:{TOPIC_LABEL} {{
  id: 'giao_dich_tai_san_quan_trong_cua_con', topic: '{TOPIC}'
}})
WHERE loai IN ['giao_dich_tai_san_quan_trong', 'trach_nhiem_lien_doi', 'tong_quat']

OPTIONAL MATCH (dk_ts:DieuKien:{TOPIC_LABEL} {{
  id: 'giao_dich_tai_san_quan_trong_can_thoa_thuan_cha_me', topic: '{TOPIC}'
}})
WHERE loai IN ['giao_dich_tai_san_quan_trong', 'trach_nhiem_lien_doi']

WITH wl, loai,
  collect(DISTINCT leaf_dd) + collect(DISTINCT dk)
    + collect(DISTINCT hv_ty) + collect(DISTINCT q_ty)
    + collect(DISTINCT nv_ld) + collect(DISTINCT hv_ts) + collect(DISTINCT dk_ts)
    AS seed_nodes,
  [x IN collect(DISTINCT leaf_dd) + collect(DISTINCT dk)
        + collect(DISTINCT hv_ty) + collect(DISTINCT q_ty)
        + collect(DISTINCT nv_ld) + collect(DISTINCT hv_ts) + collect(DISTINCT dk_ts)
   WHERE x IS NOT NULL] AS leaf_seed_nodes
"""


def _params_builder(params: DaiDienVaGiaoDichChoConParams) -> dict[str, Any]:
    loai = params.loai_van_de_dai_dien
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    td = params.tinh_trang_dai_dien_khac
    seed_ngoai_le = loai == "nguoi_dai_dien_theo_phap_luat" and td in (
        "co_nguoi_giam_ho_khac",
        "co_nguoi_dai_dien_khac",
    )
    return {
        "loai": loai,
        "seed_ngoai_le": seed_ngoai_le,
        "whitelist_dieu_ids": _DIEU_WHITELIST if use_wl else [],
    }


dai_dien_va_giao_dich_cho_con = CypherTemplate(
    name="dai_dien_va_giao_dich_cho_con",
    description=(
        "Trả lời Điều 73 về đại diện theo pháp luật và quyền thực hiện giao dịch cho con. "
        "Dùng khi hỏi ai là người đại diện, mẹ một mình mua đồ thiết yếu, "
        "hoặc bán nhà đứng tên con có cần thỏa thuận của cả hai cha mẹ không."
    ),
    params_schema=DaiDienVaGiaoDichChoConParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
