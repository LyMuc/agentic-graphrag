"""Factory helpers for xu_phat_vi_pham Cypher templates."""
from __future__ import annotations

from typing import Any, Callable, Type

from pydantic import BaseModel

from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.xu_phat_vi_pham._common import (
    TOPIC,
    TOPIC_LABEL,
    assemble_graph_seed_cypher,
    assemble_semantic_viz_from_trace_prefix,
    should_keep_whitelist,
)

BROAD = frozenset({"tong_quat", "khong_ro", "tat_ca", "chua_ro"})


def che_tai_whitelist(
    loai_che_tai: str,
    vphc_ids: list[str],
    hs_ids: list[str] | None = None,
) -> list[str]:
    hs = hs_ids or []
    if loai_che_tai == "vphc":
        return list(vphc_ids)
    if loai_che_tai == "hinh_su":
        return list(hs)
    if loai_che_tai in ("ca_hai", "khong_ro"):
        return list(vphc_ids) + list(hs)
    return list(vphc_ids)


def _seed_body(
    parent_id: str,
    router_param: str,
    *,
    dual_che_tai: bool = False,
    hs_only: bool = False,
    extra_dk_match: str = "",
) -> str:
    che_tai_block = ""
    if dual_che_tai:
        che_tai_block = f"""
OPTIONAL MATCH (parent)-[:AP_DUNG_CHE_TAI]->(ct_vphc:CheTai:{TOPIC_LABEL})
WHERE lct IN ['vphc', 'ca_hai', 'khong_ro']
  AND ct_vphc.id = 'che_tai_vi_pham_hanh_chinh'

OPTIONAL MATCH (parent)-[:AP_DUNG_CHE_TAI]->(ct_hs:CheTai:{TOPIC_LABEL})
WHERE lct IN ['hinh_su', 'ca_hai', 'khong_ro']
  AND ct_hs.id = 'che_tai_trach_nhiem_hinh_su'
"""
    elif hs_only:
        che_tai_block = f"""
OPTIONAL MATCH (parent)-[:AP_DUNG_CHE_TAI]->(ct_hs:CheTai:{TOPIC_LABEL})
WHERE ct_hs.id = 'che_tai_trach_nhiem_hinh_su'
"""
    else:
        che_tai_block = f"""
OPTIONAL MATCH (parent)-[:AP_DUNG_CHE_TAI]->(ct_vphc:CheTai:{TOPIC_LABEL})
WHERE ct_vphc.id = 'che_tai_vi_pham_hanh_chinh'
"""

    dk_block = ""
    if extra_dk_match:
        dk_block = f"""
OPTIONAL MATCH (parent)-[:BAO_GOM|AP_DUNG_KHI]->(dk:DieuKien:{TOPIC_LABEL})
WHERE {extra_dk_match}
"""

    ct_collect = ""
    if dual_che_tai:
        ct_collect = " + collect(DISTINCT ct_vphc) + collect(DISTINCT ct_hs)"
    elif hs_only:
        ct_collect = " + collect(DISTINCT ct_hs)"
    else:
        ct_collect = " + collect(DISTINCT ct_vphc)"

    dk_collect = " + collect(DISTINCT dk)" if extra_dk_match else ""

    return f"""
WITH ${router_param} AS rp, $leaf_id AS leaf_id, $loai_che_tai AS lct,
     $whitelist_dieu_ids AS wl, $khia_canh_che_tai AS kcc

OPTIONAL MATCH (parent:QuyDinh:{TOPIC_LABEL} {{id: '{parent_id}', topic: '{TOPIC}'}})

OPTIONAL MATCH (parent)-[:BAO_GOM]->(leaf)
WHERE leaf IS NOT NULL
  AND (rp IN ['tong_quat', 'khong_ro'] OR leaf.id = leaf_id)
{che_tai_block}{dk_block}
WITH wl, rp, lct, kcc,
  (collect(DISTINCT parent) + collect(DISTINCT leaf){ct_collect}{dk_collect}) AS seed_nodes,
  CASE
    WHEN NOT (rp IN ['tong_quat', 'khong_ro'])
         AND size([x IN collect(DISTINCT leaf) WHERE x IS NOT NULL]) > 0
      THEN [x IN collect(DISTINCT leaf) WHERE x IS NOT NULL]
    ELSE [x IN collect(DISTINCT parent) + collect(DISTINCT leaf){dk_collect}
         WHERE x IS NOT NULL]
  END AS leaf_seed_nodes
"""


def make_parent_leaf_template(
    *,
    name: str,
    description: str,
    params_schema: Type[BaseModel],
    parent_id: str,
    router_field: str,
    leaf_map: dict[str, str],
    vphc_whitelist: list[str],
    hs_whitelist: list[str] | None = None,
    dual_che_tai: bool = False,
    hs_only: bool = False,
    extra_router_fields: tuple[str, ...] = (),
    extra_dk_match: str = "",
    fixed_loai_che_tai: str | None = None,
) -> CypherTemplate:
    router_fields = (router_field,) + extra_router_fields
    seed = _seed_body(
        parent_id,
        router_field,
        dual_che_tai=dual_che_tai,
        hs_only=hs_only,
        extra_dk_match=extra_dk_match,
    )

    if fixed_loai_che_tai:
        loai_default = fixed_loai_che_tai
    elif hs_only:
        loai_default = "hinh_su"
    elif dual_che_tai:
        loai_default = "khong_ro"
    else:
        loai_default = "vphc"

    def _params_builder(params: BaseModel) -> dict[str, Any]:
        data = params.model_dump()
        rp = data.get(router_field, "tong_quat")
        leaf_id = leaf_map.get(rp, "") or leaf_map.get("khong_ro", "")
        lct = fixed_loai_che_tai or data.get("loai_che_tai", loai_default)
        use_wl = should_keep_whitelist(params, router_fields) or lct in (
            "ca_hai",
            "khong_ro",
        )
        wl = che_tai_whitelist(lct, vphc_whitelist, hs_whitelist) if use_wl else []
        out: dict[str, Any] = {
            router_field: rp,
            "leaf_id": leaf_id,
            "loai_che_tai": lct,
            "khia_canh_che_tai": data.get("khia_canh_che_tai", "tong_quat"),
            "whitelist_dieu_ids": wl,
        }
        for k, v in data.items():
            if k not in out:
                out[k] = v
        return out

    def _builder_wrapper(params: BaseModel) -> dict[str, Any]:
        data = params.model_dump()
        data.setdefault("loai_che_tai", loai_default)
        data.setdefault("khia_canh_che_tai", "tong_quat")
        if fixed_loai_che_tai:
            data["loai_che_tai"] = fixed_loai_che_tai
        rebuilt = params.__class__(**{k: v for k, v in data.items() if k in params.model_fields})
        out = _params_builder(rebuilt)
        out["loai_che_tai"] = data["loai_che_tai"]
        out["khia_canh_che_tai"] = data.get("khia_canh_che_tai", "tong_quat")
        return out

    return CypherTemplate(
        name=name,
        description=description,
        params_schema=params_schema,
        cypher=assemble_graph_seed_cypher(seed),
        viz_cypher=assemble_semantic_viz_from_trace_prefix(seed),
        params_builder=_builder_wrapper,
    )
