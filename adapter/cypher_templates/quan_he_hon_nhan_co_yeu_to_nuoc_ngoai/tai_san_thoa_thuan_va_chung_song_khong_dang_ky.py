"""Template — tài sản thỏa thuận và chung sống không đăng ký (Đ130)."""
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

_ROUTER_FIELDS = ("dang_quan_he",)
_DIEU_WHITELIST = ["Luat_HNGD_2014_Dieu_130"]


class TaiSanVaChungSongParams(BaseModel):
    dang_quan_he: Literal[
        "che_do_tai_san_vo_chong_theo_thoa_thuan",
        "chung_song_nhu_vo_chong_khong_dang_ky",
        "khong_ro",
    ] = Field(
        description=(
            "chế độ tài sản theo thỏa thuận → che_do_tai_san_vo_chong_theo_thoa_thuan; "
            "chung sống không đăng ký → chung_song_nhu_vo_chong_khong_dang_ky."
        )
    )
    yeu_cau_giai_quyet: Literal[
        "ap_dung_che_do_tai_san",
        "hau_qua_chung_song",
        "chia_tai_san_khi_cham_dut",
        "phap_luat_ap_dung",
        "tong_quat",
    ] = Field(description="chia tài sản khi chấm dứt → chia_tai_san_khi_cham_dut.")


_SEED_BODY = f"""
WITH $dang_quan_he AS dq, $yeu_cau_giai_quyet AS yc, $whitelist_dieu_ids AS wl

OPTIONAL MATCH (l_thoa:HanhVi:{TOPIC_LABEL} {{
  id: 'yeu_cau_ap_dung_che_do_tai_san_vo_chong_theo_thoa_thuan', topic: '{TOPIC}'
}})
WHERE dq IN ['che_do_tai_san_vo_chong_theo_thoa_thuan', 'khong_ro']
  OR yc = 'ap_dung_che_do_tai_san'

OPTIONAL MATCH (l_cs:QuanHe:{TOPIC_LABEL} {{
  id: 'chung_song_nhu_vo_chong_khong_dang_ky_co_yeu_to_nuoc_ngoai', topic: '{TOPIC}'
}})
WHERE dq IN ['chung_song_nhu_vo_chong_khong_dang_ky', 'khong_ro']
  OR yc IN ['hau_qua_chung_song', 'chia_tai_san_khi_cham_dut']

OPTIONAL MATCH (l_hq:HauQua:{TOPIC_LABEL} {{
  id: 'hau_qua_tai_san_khi_cham_dut_chung_song', topic: '{TOPIC}'
}})
WHERE yc IN ['chia_tai_san_khi_cham_dut', 'hau_qua_chung_song', 'tong_quat']

OPTIONAL MATCH (l_cq:CoQuan:{TOPIC_LABEL} {{
  id: 'co_quan_co_tham_quyen_viet_nam_giai_quyet', topic: '{TOPIC}'
}})
OPTIONAL MATCH (l_qd:QuyDinh:{TOPIC_LABEL} {{
  id: 'ap_dung_luat_hon_nhan_gia_dinh_va_luat_viet_nam_lien_quan', topic: '{TOPIC}'
}})

WITH wl, dq, yc,
  collect(DISTINCT l_thoa) + collect(DISTINCT l_cs) + collect(DISTINCT l_hq)
    + collect(DISTINCT l_cq) + collect(DISTINCT l_qd) AS seed_nodes,
  CASE
    WHEN yc = 'ap_dung_che_do_tai_san' THEN
      [x IN collect(DISTINCT l_thoa) + collect(DISTINCT l_cq) + collect(DISTINCT l_qd)
       WHERE x IS NOT NULL]
    WHEN yc = 'chia_tai_san_khi_cham_dut' THEN
      [x IN collect(DISTINCT l_cs) + collect(DISTINCT l_hq) + collect(DISTINCT l_cq)
           + collect(DISTINCT l_qd)
       WHERE x IS NOT NULL]
    WHEN dq = 'chung_song_nhu_vo_chong_khong_dang_ky' THEN
      [x IN collect(DISTINCT l_cs) + collect(DISTINCT l_hq) + collect(DISTINCT l_cq)
           + collect(DISTINCT l_qd)
       WHERE x IS NOT NULL]
    WHEN dq = 'che_do_tai_san_vo_chong_theo_thoa_thuan' THEN
      [x IN collect(DISTINCT l_thoa) + collect(DISTINCT l_cq) + collect(DISTINCT l_qd)
       WHERE x IS NOT NULL]
    ELSE
      [x IN collect(DISTINCT l_thoa) + collect(DISTINCT l_cs) + collect(DISTINCT l_hq)
           + collect(DISTINCT l_cq) + collect(DISTINCT l_qd)
       WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def _params_builder(params: TaiSanVaChungSongParams) -> dict[str, Any]:
    use_wl = should_keep_whitelist(params, _ROUTER_FIELDS)
    return {
        "dang_quan_he": params.dang_quan_he,
        "yeu_cau_giai_quyet": params.yeu_cau_giai_quyet,
        "whitelist_dieu_ids": _DIEU_WHITELIST if use_wl else [],
    }


tai_san_thoa_thuan_va_chung_song_khong_dang_ky = CypherTemplate(
    name="tai_san_thoa_thuan_va_chung_song_khong_dang_ky",
    description=(
        "Dùng cho hai nhánh Điều 130: áp dụng chế độ tài sản vợ chồng theo thỏa thuận "
        "và giải quyết hậu quả chung sống như vợ chồng không đăng ký kết hôn có yếu tố "
        "nước ngoài. Cơ quan Việt Nam áp dụng Luật Hôn nhân và gia đình cùng luật liên quan. "
        "Ví dụ: Yêu cầu áp dụng chế độ tài sản theo thỏa thuận được giải quyết thế nào?; "
        "Chia tài sản khi chấm dứt chung sống không đăng ký kết hôn?"
    ),
    params_schema=TaiSanVaChungSongParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
