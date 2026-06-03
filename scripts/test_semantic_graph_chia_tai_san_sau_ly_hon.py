"""Smoke test Cypher semantic graph cho 6 template chia_tai_san_sau_ly_hon."""
from __future__ import annotations

import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adapter.config import driver
from adapter.cypher_templates.chia_tai_san_sau_ly_hon import (
    CHIA_TAI_SAN_SAU_LY_HON_REGISTRY,
)


def _today_str() -> str:
    return date.today().isoformat()


def _run(template_name: str, params: dict) -> list[str]:
    tpl = CHIA_TAI_SAN_SAU_LY_HON_REGISTRY.get(template_name)
    merged = {
        **tpl.params_builder(tpl.params_schema(**params)),
        "target_date": _today_str(),
    }
    with driver.session() as session:
        row = session.run(tpl.cypher, merged).single()
    if row is None:
        raise RuntimeError(f"Query returned no rows for {template_name} {params}")
    ctx = row["Context_Tho"]
    return sorted({x["id_thuc_te_ap_dung"] for x in ctx["can_cu_chinh"]})


def _check(
    ok: int,
    total: int,
    name: str,
    params: dict,
    got: set[str],
    *,
    must_include: set[str] | None = None,
    must_exclude: set[str] | None = None,
) -> tuple[int, int]:
    total += 1
    bad = False
    if must_include and not (must_include <= got):
        bad = True
        print(f"FAIL {name} {params}")
        print(f"  missing: {sorted(must_include - got)}")
    if must_exclude and (got & must_exclude):
        bad = True
        print(f"FAIL {name} {params}")
        print(f"  forbidden hit: {sorted(got & must_exclude)}")
    if bad:
        print(f"  got: {sorted(got)}")
        return ok, total
    print(f"PASS {name} {params}")
    return ok + 1, total


def main() -> None:
    ok = 0
    total = 0

    # Regression: yeu_to_chia — 4 Điểm K2, không K1/3/4/5/6
    got = set(_run("nguyen_tac_chia_tai_san_ly_hon", {"khia_canh": "yeu_to_chia"}))
    diem = {x for x in got if "_Diem_" in x}
    ok, total = _check(
        ok,
        total,
        "nguyen_tac yeu_to_chia",
        {"khia_canh": "yeu_to_chia"},
        got,
        must_include={
            "Luat_HNGD_2014_Dieu_59_Khoan_2_Diem_a",
            "Luat_HNGD_2014_Dieu_59_Khoan_2_Diem_b",
            "Luat_HNGD_2014_Dieu_59_Khoan_2_Diem_c",
            "Luat_HNGD_2014_Dieu_59_Khoan_2_Diem_d",
        },
        must_exclude={
            "Luat_HNGD_2014_Dieu_59_Khoan_1",
            "Luat_HNGD_2014_Dieu_59_Khoan_3",
            "Luat_HNGD_2014_Dieu_59_Khoan_4",
            "Luat_HNGD_2014_Dieu_59_Khoan_5",
            "Luat_HNGD_2014_Dieu_59_Khoan_6",
        },
    )
    if diem != {
        "Luat_HNGD_2014_Dieu_59_Khoan_2_Diem_a",
        "Luat_HNGD_2014_Dieu_59_Khoan_2_Diem_b",
        "Luat_HNGD_2014_Dieu_59_Khoan_2_Diem_c",
        "Luat_HNGD_2014_Dieu_59_Khoan_2_Diem_d",
    }:
        print("  (diem set mismatch:", sorted(diem), ")")

    # leaf-first: Đ61 K1 only when không xác định được
    ok, total = _check(
        ok,
        total,
        "truong_hop xdp=khong",
        {
            "loai_truong_hop": "song_chung_voi_gia_dinh",
            "xac_dinh_duoc_phan_tai_san": "khong",
        },
        set(
            _run(
                "truong_hop_nha_o_gia_dinh_va_luu_cu",
                {
                    "loai_truong_hop": "song_chung_voi_gia_dinh",
                    "xac_dinh_duoc_phan_tai_san": "khong",
                },
            )
        ),
        must_include={"Luat_HNGD_2014_Dieu_61_Khoan_1"},
        must_exclude={"Luat_HNGD_2014_Dieu_61_Khoan_2"},
    )

    ok, total = _check(
        ok,
        total,
        "truong_hop xdp=co",
        {
            "loai_truong_hop": "song_chung_voi_gia_dinh",
            "xac_dinh_duoc_phan_tai_san": "co",
        },
        set(
            _run(
                "truong_hop_nha_o_gia_dinh_va_luu_cu",
                {
                    "loai_truong_hop": "song_chung_voi_gia_dinh",
                    "xac_dinh_duoc_phan_tai_san": "co",
                },
            )
        ),
        must_include={"Luat_HNGD_2014_Dieu_61_Khoan_2"},
        must_exclude={"Luat_HNGD_2014_Dieu_61_Khoan_1"},
    )

    cases = [
        (
            "nguyen_tac_chia_tai_san_ly_hon",
            {"khia_canh": "thoa_thuan"},
            {"Luat_HNGD_2014_Dieu_59_Khoan_1"},
            None,
        ),
        (
            "nghia_vu_tai_san_voi_nguoi_thu_ba_khi_ly_hon",
            {"loai_nghia_vu": "tranh_chap"},
            {
                "Luat_HNGD_2014_Dieu_60_Khoan_1",
                "Luat_HNGD_2014_Dieu_60_Khoan_2",
            },
            None,
        ),
        (
            "tai_san_chung_dua_vao_kinh_doanh_khi_ly_hon",
            {"nguoi_dang_kinh_doanh": "chong"},
            {"Luat_HNGD_2014_Dieu_64"},
            None,
        ),
        (
            "chia_quyen_su_dung_dat_khi_ly_hon",
            {"tinh_chat_qsd_dat": "rieng"},
            {"Luat_HNGD_2014_Dieu_62_Khoan_1"},
            {"Luat_HNGD_2014_Dieu_62_Khoan_2", "Luat_HNGD_2014_Dieu_62_Khoan_3"},
        ),
    ]
    for name, params, must_include, must_exclude in cases:
        got = set(_run(name, params))
        ok, total = _check(
            ok, total, name, params, got,
            must_include=must_include,
            must_exclude=must_exclude,
        )

    print(f"\n{ok}/{total} passed")
    if ok != total:
        sys.exit(1)


if __name__ == "__main__":
    main()
