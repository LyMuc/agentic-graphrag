"""Template — tình nghĩa vợ chồng (Đ19 khoản 1)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.quyen_nghia_vu_vo_chong._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
)

_KHIA_CANH_TO_NGHIA_VU: dict[str, str] = {
    "thuong_yeu": "nghia_vu_thuong_yeu",
    "chung_thuy": "nghia_vu_chung_thuy",
    "ton_trong_quan_tam_cham_soc_giup_do": "nghia_vu_quan_tam_cham_soc_giup_do",
    "chia_se_cong_viec_gia_dinh": "nghia_vu_chia_se_thuc_hien_cong_viec_gia_dinh",
}


class TinhNghiaVoChongParams(BaseModel):
    khia_canh_tinh_nghia: Literal[
        "thuong_yeu",
        "chung_thuy",
        "ton_trong_quan_tam_cham_soc_giup_do",
        "chia_se_cong_viec_gia_dinh",
        "khong_deo_nhan_cuoi",
        "liet_ke_nghia_vu",
        "tong_quat",
        "khong_ro",
    ] = Field(description="chung thủy/quan hệ tình cảm -> chung_thuy; nhẫn cưới -> khong_deo_nhan_cuoi.")
    pham_vi_tinh_nghia: Literal[
        "khoan_1",
        "toan_bo_dieu_19",
        "khong_ro",
    ] = Field(description="câu chung tình nghĩa vợ chồng -> toan_bo_dieu_19; nghĩa vụ khoản 1 -> khoan_1.")


_SEED_BODY = f"""
WITH $kc AS kc, $pv AS pv, $nv_id AS nv_id,
     $seed_toan_bo AS seed_toan_bo, $seed_liet_ke AS seed_liet_ke,
     $seed_chung_thuy AS seed_chung_thuy, $seed_nhan AS seed_nhan,
     $whitelist_dieu_ids AS wl

OPTIONAL MATCH (anchor:QuyDinh:{TOPIC_LABEL} {{
  id: 'tinh_nghia_vo_chong', topic: '{TOPIC}'
}})
WHERE seed_toan_bo = true OR seed_liet_ke = true OR nv_id <> ''

OPTIONAL MATCH (nv:NghiaVu:{TOPIC_LABEL} {{id: nv_id, topic: '{TOPIC}'}})
WHERE nv_id <> ''

OPTIONAL MATCH (nv_all:NghiaVu:{TOPIC_LABEL})
WHERE seed_liet_ke = true OR seed_toan_bo = true
  AND nv_all.id IN [
    'nghia_vu_thuong_yeu', 'nghia_vu_chung_thuy', 'nghia_vu_ton_trong_lan_nhau',
    'nghia_vu_quan_tam_cham_soc_giup_do', 'nghia_vu_chia_se_thuc_hien_cong_viec_gia_dinh'
  ]
  AND nv_all.topic = '{TOPIC}'

OPTIONAL MATCH (nv_sc:NghiaVu:{TOPIC_LABEL} {{
  id: 'nghia_vu_song_chung', topic: '{TOPIC}'
}})
WHERE seed_toan_bo = true

OPTIONAL MATCH (hv_ct:HanhVi:{TOPIC_LABEL} {{
  id: 'quan_he_tinh_cam_voi_nguoi_khac_khi_dang_hon_nhan', topic: '{TOPIC}'
}})
WHERE seed_chung_thuy = true
OPTIONAL MATCH (hq_ct:HauQua:{TOPIC_LABEL} {{
  id: 'dau_hieu_vi_pham_nghia_vu_chung_thuy', topic: '{TOPIC}'
}})
WHERE seed_chung_thuy = true

OPTIONAL MATCH (hv_nc:HanhVi:{TOPIC_LABEL} {{id: 'khong_deo_nhan_cuoi', topic: '{TOPIC}'}})
WHERE seed_nhan = true
OPTIONAL MATCH (qd_nc:QuyDinh:{TOPIC_LABEL} {{
  id: 'khong_deo_nhan_cuoi_khong_tu_dong_vi_pham_tinh_nghia_vo_chong', topic: '{TOPIC}'
}})
WHERE seed_nhan = true

WITH wl, kc,
  collect(DISTINCT anchor) + collect(DISTINCT nv) + collect(DISTINCT nv_sc)
    + collect(DISTINCT nv_all) + collect(DISTINCT hv_ct) + collect(DISTINCT hq_ct)
    + collect(DISTINCT hv_nc) + collect(DISTINCT qd_nc)
    AS seed_nodes,
  [x IN collect(DISTINCT nv) + collect(DISTINCT nv_sc) + collect(DISTINCT nv_all)
       + collect(DISTINCT hv_ct) + collect(DISTINCT hq_ct)
       + collect(DISTINCT hv_nc) + collect(DISTINCT qd_nc)
   WHERE x IS NOT NULL] AS leaf_seed_nodes
"""


def _params_builder(params: TinhNghiaVoChongParams) -> dict[str, Any]:
    kc = params.khia_canh_tinh_nghia
    pv = params.pham_vi_tinh_nghia
    seed_liet_ke = kc == "liet_ke_nghia_vu" or (
        pv == "khoan_1" and kc in ("tong_quat", "khong_ro")
    )
    seed_toan_bo = pv == "toan_bo_dieu_19" or (
        kc == "tong_quat" and pv != "khoan_1" and not seed_liet_ke
    )
    if kc == "liet_ke_nghia_vu":
        seed_liet_ke = True
        seed_toan_bo = False
    nv_id = ""
    if not seed_liet_ke and not seed_toan_bo:
        if kc == "chung_thuy":
            nv_id = "nghia_vu_chung_thuy"
        elif kc in _KHIA_CANH_TO_NGHIA_VU:
            nv_id = _KHIA_CANH_TO_NGHIA_VU[kc]
    seed_chung_thuy = kc == "chung_thuy"
    seed_nhan = kc == "khong_deo_nhan_cuoi"
    return {
        "kc": kc,
        "pv": pv,
        "nv_id": nv_id,
        "seed_toan_bo": seed_toan_bo,
        "seed_liet_ke": seed_liet_ke,
        "seed_chung_thuy": seed_chung_thuy,
        "seed_nhan": seed_nhan,
        "whitelist_dieu_ids": [],
    }


tinh_nghia_vo_chong = CypherTemplate(
    name="tinh_nghia_vo_chong",
    description=(
        "Xử lý Điều 19 khoản 1 về thương yêu, chung thủy, tôn trọng, quan tâm, chăm sóc, "
        "giúp đỡ và chia sẻ công việc gia đình; câu hỏi chung tình nghĩa vợ chồng có thể "
        "lấy cả khoản 1 và khoản 2. "
        "Ví dụ: Vợ chồng có những nghĩa vụ gì tại khoản 1 Điều 19?; "
        "Quan hệ tình cảm với người khác có vi phạm chung thủy?; "
        "Không đeo nhẫn cưới có vi phạm tình nghĩa vợ chồng?"
    ),
    params_schema=TinhNghiaVoChongParams,
    cypher=assemble_graph_seed_cypher(_SEED_BODY),
    viz_cypher=assemble_semantic_viz_from_trace_prefix(_SEED_BODY),
    params_builder=_params_builder,
)
