# KG Schema (Neo4j)

Tóm tắt schema **thực tế trong code** — dùng khi viết Chương 5. Chi tiết đầy đủ: `5_Giai_phap_dong_gop.tex` bảng nhãn nút.

## Legal layer — Node labels (manual)

| Label | Ý nghĩa |
|---|---|
| `Luat`, `NghiDinh`, `ThongTu`, `NghiQuyet` | Văn bản QPPL |
| `DieuLuat`, `DieuKhoanLuat`, `DieuKhoanDiemLuat` | Cấu trúc điều/khoản/điểm |

Thuộc tính chính: `id`, `so_hieu`, `ngay_co_hieu_luc`, `ngay_het_hieu_luc`, `tinh_trang_hieu_luc`, `cap_bac_phap_ly`, `noidung`, `dieu`, `khoan`, `diem`.

## Legal layer — Relationships (auto từ code)

<!-- BEGIN AUTO-GENERATED:sync_thesis_context.py -->
_Cập nhật lúc 2026-06-13 08:52 UTC_

Trích từ `adapter/retrievers/_context_tho_common.py` (pattern `[:REL]` trong Cypher):

| Relationship |
|---|
| `CO_DIEM` |
| `CO_KHOAN` |
| `DUOC_SUA_DOI_BOI` |
| `HUONG_DAN_BOI` |

Tổng: **4** quan hệ được quét tự động.
<!-- END AUTO-GENERATED:sync_thesis_context.py -->
