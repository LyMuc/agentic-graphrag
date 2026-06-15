"""Smoke test: 9 Cypher templates fixed for Neo4j aggregation grouping. Neo4j only — no LLM/API."""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from adapter.config import driver
from adapter.cypher_templates.cha_me_con_sau_ly_hon.nuoi_con_duoi_36_thang import (
    NuoiConDuoi36ThangParams,
    nuoi_con_duoi_36_thang,
)
from adapter.cypher_templates.chia_tai_san_sau_ly_hon.tai_san_cu_the_khi_ly_hon import (
    TaiSanCuTheKhiLyHonParams,
    tai_san_cu_the_khi_ly_hon,
)
from adapter.cypher_templates.dieu_kien_ket_hon.anh_huong_tinh_trang_ca_nhan import (
    AnhHuongTinhTrangCaNhanParams,
    anh_huong_tinh_trang_ca_nhan,
)
from adapter.cypher_templates.dieu_kien_ket_hon.quan_he_huyet_thong_va_ba_doi import (
    QuanHeHuyetThongVaBaDoiParams,
    quan_he_huyet_thong_va_ba_doi,
)
from adapter.cypher_templates.ket_hon_trai_phap_luat.hau_qua_phap_ly_huy_ket_hon_trai_phap_luat import (
    HauQuaPhapLyHuyKetHonTraiPhapLuatParams,
    hau_qua_phap_ly_huy_ket_hon_trai_phap_luat,
)
from adapter.cypher_templates.quan_he_giua_cac_thanh_vien_khac_trong_gia_dinh.nuoi_duong_giua_co_di_chu_cau_bac_ruot_va_chau_ruot import (
    NuoiDuongGiuaHoHangVaChauParams,
    nuoi_duong_giua_co_di_chu_cau_bac_ruot_va_chau_ruot,
)
from adapter.cypher_templates.quy_dinh_chung_khai_niem_phap_ly.nguyen_tac_che_do_hon_nhan_gia_dinh import (
    NguyenTacCheDoHonNhanGiaDinhParams,
    nguyen_tac_che_do_hon_nhan_gia_dinh,
)
from adapter.cypher_templates.quy_dinh_chung_khai_niem_phap_ly.pham_vi_ba_doi_va_quan_he_than_thich import (
    PhamViBaDoiVaQuanHeThanThichParams,
    pham_vi_ba_doi_va_quan_he_than_thich,
)
from adapter.cypher_templates.quy_dinh_chung_khai_niem_phap_ly.trach_nhiem_nha_nuoc_xa_hoi import (
    TrachNhiemNhaNuocXaHoiParams,
    trach_nhiem_nha_nuoc_xa_hoi,
)

TARGET = date.today().strftime("%Y-%m-%d")

CASES = [
    (
        nuoi_con_duoi_36_thang,
        NuoiConDuoi36ThangParams(
            do_tuoi_con="duoi_36_thang",
            tinh_trang_nguoi_me="khong_du_dieu_kien",
            thoa_thuan_khac="khong_ro",
            ben_de_nghi_nuoi="cha",
            co_yeu_cau_cap_duong="khong_ro",
        ),
    ),
    (
        nuoi_duong_giua_co_di_chu_cau_bac_ruot_va_chau_ruot,
        NuoiDuongGiuaHoHangVaChauParams(
            doi_tuong_ho_hang="khong_ro",
            chieu_nuoi_duong_ho_hang="khong_ro",
            khia_canh_nuoi_duong_ho_hang="dieu_kien_phat_sinh",
            con_cha_me_cua_nguoi_can_nuoi_duong="khong",
            con_con_cua_nguoi_can_nuoi_duong="khong",
            tinh_trang_nguoi_thuoc_dieu_104_105="khong_ro",
        ),
    ),
    (
        pham_vi_ba_doi_va_quan_he_than_thich,
        PhamViBaDoiVaQuanHeThanThichParams(
            loai_quan_he="ho_trong_pham_vi_ba_doi",
            khia_canh_ba_doi="tong_quat",
        ),
    ),
    (
        nguyen_tac_che_do_hon_nhan_gia_dinh,
        NguyenTacCheDoHonNhanGiaDinhParams(
            khia_canh_nguyen_tac="tong_quat",
            muc_do_chi_tiet="tom_tat",
        ),
    ),
    (
        trach_nhiem_nha_nuoc_xa_hoi,
        TrachNhiemNhaNuocXaHoiParams(
            khia_canh_trach_nhiem="tong_quat",
            chu_the_trach_nhiem="khong_ro",
        ),
    ),
    (
        quan_he_huyet_thong_va_ba_doi,
        QuanHeHuyetThongVaBaDoiParams(
            loai_quan_he_huyet_thong="khong_ro",
            khia_canh_ba_doi="tong_quat",
            co_chung_goc_sinh_ra="khong_ro",
        ),
    ),
    (
        anh_huong_tinh_trang_ca_nhan,
        AnhHuongTinhTrangCaNhanParams(
            hoan_canh_ca_nhan="khong_ro",
            tinh_trang_nang_luc_hanh_vi="khong_ro",
            khia_canh_anh_huong="tong_quat",
        ),
    ),
    (
        hau_qua_phap_ly_huy_ket_hon_trai_phap_luat,
        HauQuaPhapLyHuyKetHonTraiPhapLuatParams(
            khia_canh_hau_qua="tong_quat",
            tinh_huong_quan_he="da_bi_huy",
            co_con_chung="khong",
            co_tranh_chap_tai_san="khong",
            co_yeu_cau_thua_ke="khong",
        ),
    ),
    (
        tai_san_cu_the_khi_ly_hon,
        TaiSanCuTheKhiLyHonParams(
            loai_tai_san="khong_ro",
            nguon_goc="khong_ro",
        ),
    ),
]


def main() -> int:
    ok = 0
    fail = 0
    for tpl, params in CASES:
        runtime = tpl.build_params(params)
        runtime["target_date"] = TARGET
        try:
            records, _, _ = driver.execute_query(tpl.cypher, **runtime)
            has_ctx = bool(records) and "Context_Tho" in records[0].data()
            cc = (
                len((records[0].data().get("Context_Tho") or {}).get("can_cu_chinh") or [])
                if has_ctx
                else 0
            )
            print(f"OK  {tpl.name}: records={len(records)}, can_cu_chinh={cc}")
            ok += 1
        except Exception as exc:
            print(f"FAIL {tpl.name}: {exc}")
            fail += 1

    print(f"\nSummary: {ok} passed, {fail} failed")
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
