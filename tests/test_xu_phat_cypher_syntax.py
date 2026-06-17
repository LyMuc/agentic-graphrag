"""Smoke test: Cypher syntax cho toàn bộ registry xu_phat_vi_pham."""
from __future__ import annotations

import typing

import pytest
from pydantic import BaseModel

from adapter.config import driver
from adapter.cypher_templates.xu_phat_vi_pham import XU_PHAT_VI_PHAM_REGISTRY


def _default_for_field(field_name: str, annotation: typing.Any) -> typing.Any:
    origin = typing.get_origin(annotation)
    if origin is typing.Literal:
        args = typing.get_args(annotation)
        if "tong_quat" in args:
            return "tong_quat"
        return args[0]
    if field_name == "loai_che_tai":
        return "vphc"
    if field_name == "khia_canh_che_tai":
        return "tong_quat"
    return None


def _minimal_params(schema: type[BaseModel]) -> BaseModel:
    data: dict[str, typing.Any] = {}
    for name, field in schema.model_fields.items():
        val = _default_for_field(name, field.annotation)
        if val is not None:
            data[name] = val
    return schema(**data)


@pytest.mark.parametrize(
    "template_name",
    list(XU_PHAT_VI_PHAM_REGISTRY.descriptions().keys()),
)
def test_xu_phat_template_cypher_parses(template_name: str) -> None:
    template = XU_PHAT_VI_PHAM_REGISTRY.get(template_name)
    params = _minimal_params(template.params_schema)
    runtime = template.params_builder(params)
    runtime["target_date"] = "2021-12-31"
    runtime["query_date"] = "2026-06-16"

    driver.execute_query(f"EXPLAIN {template.cypher}", **runtime)


def test_tao_hon_regression_includes_dieu5_khoan2_diem_b() -> None:
    """Regression: tảo hôn năm 2021 phải seed Điều 5 khoản 2 điểm b."""
    template = XU_PHAT_VI_PHAM_REGISTRY.get("tao_hon_va_to_chuc_tao_hon")
    from adapter.cypher_templates.xu_phat_vi_pham.tao_hon_va_to_chuc_tao_hon import (
        TaoHonVaToChucTaoHonParams,
    )

    params = TaoHonVaToChucTaoHonParams(
        dang_hanh_vi="ket_hon_chua_du_tuoi",
        loai_che_tai="vphc",
        khia_canh_che_tai="tong_quat",
    )
    runtime = template.params_builder(params)
    runtime["target_date"] = "2021-12-31"
    runtime["query_date"] = "2026-06-16"
    assert "Luat_HNGD_2014_Dieu_5_Khoan_2_Diem_b" in runtime["whitelist_dieu_ids"]

    records, _, _ = driver.execute_query(template.cypher, **runtime)
    ctx = records[0]["Context_Tho"]
    assert ctx.get("can_cu_chinh")
    all_ids = {x["id_thuc_te_ap_dung"] for x in ctx["can_cu_chinh"]}
    bo_tro_ids = {x["id"] for x in ctx.get("can_cu_bo_tro", []) if x.get("id")}
    assert (
        "Luat_HNGD_2014_Dieu_5_Khoan_2_Diem_b" in all_ids
        or "Luat_HNGD_2014_Dieu_5_Khoan_2_Diem_b" in bo_tro_ids
        or any("Dieu_5_Khoan_2" in i for i in all_ids | bo_tro_ids)
    )


def test_hanh_vi_bi_cam_hngd_tong_quat_registry() -> None:
    assert XU_PHAT_VI_PHAM_REGISTRY.get("hanh_vi_bi_cam_hngd_tong_quat") is not None
    assert len(XU_PHAT_VI_PHAM_REGISTRY.names()) == 29
