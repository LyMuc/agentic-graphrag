"""Shared param types for topic xu_phat_vi_pham."""
from __future__ import annotations

from typing import Literal

from pydantic import Field

LoaiCheTai = Literal["vphc", "hinh_su", "ca_hai", "khong_ro"]
KhiaCanhCheTai = Literal[
    "muc_phat",
    "dieu_kien_ap_dung",
    "hinh_thuc_bo_sung",
    "bien_phap_khac_phuc",
    "tong_quat",
]

LOAI_CHE_TAI_FIELD = Field(
    description=(
        "Nhánh chế tài. Map: phạt tiền/phạt hành chính → vphc; "
        "truy cứu TNHS/phạt tù → hinh_su; toàn bộ chế tài → ca_hai; "
        "không rõ → khong_ro."
    )
)

KHIA_CANH_CHE_TAI_FIELD = Field(
    description=(
        "Góc hỏi chế tài. Map: mức phạt → muc_phat; điều kiện truy cứu → "
        "dieu_kien_ap_dung; tịch thu/đình chỉ → hinh_thuc_bo_sung; "
        "buộc xin lỗi/trả tài sản → bien_phap_khac_phuc; không rõ → tong_quat."
    )
)
