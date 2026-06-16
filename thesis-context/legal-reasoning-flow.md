# Legal Reasoning Flow

Pipeline thực tế từ câu hỏi → context chuẩn hóa cho Response LLM.

## Sơ đồ

```text
User query
  → Router (application/router.py) chọn retriever(s)
  → Retriever LLM trong adapter/retrievers/
       • phân loại một hoặc nhiều Cypher template
       • trích xuất params + thoi_diem_su_kien (optional)
  → Retriever thực thi Cypher template đã chọn
  → Neo4j → record Context_Tho
  → chuan_hoa_Context_cho_LLM (utils/utils.py)
  → Response LLM (presentation/main.py main_prompt)
```

## Giai đoạn 1 — Truy xuất trên đồ thị (Cypher)

Implement trong `adapter/cypher_templates/*/_common.py`, dùng snippet chung từ
`adapter/retrievers/_context_tho_common.py`:

1. Match seed điều/khoản/điểm (từ IDs hoặc semantic graph).
2. Expand cấu trúc (`CO_KHOAN`, `CO_DIEM`) và heading cha.
3. `THAY_THE_BOI` có hướng (moi/cu) — lọc theo `$target_date`.
4. `DUOC_SUA_DOI_BOI`, `HUONG_DAN_BOI`, mở rộng chi tiết hướng dẫn.
5. `THAM_CHIEU_DEN` / ancestor collect (`_context_tho_common.py`).
6. `quy_dinh_hien_hanh_doi_chieu` (thay thế về phía tương lai).
7. (Optional) `can_cu_sap_hieu_luc` khi không có mốc thời gian user.

## Giai đoạn 2 — Chuẩn hóa (`chuan_hoa_Context_cho_LLM`)

File: `utils/utils.py` (hàm `chuan_hoa_Context_cho_LLM`).

| Bước algorithm trong đồ án | Code |
|---|---|
| Thay nội dung bởi văn bản sửa đổi | `id_sua_doi`, `FLAG_CANH_BAO_SUA_DOI` |
| Phân loại hướng dẫn / bổ trợ | `danh_sach_huong_dan`, `danh_sach_bo_tro` |
| Cờ ưu tiên cấp bậc | `FLAG_CANH_BAO_THU_TU_UU_TIEN` |
| Cờ lịch sử | `FLAG_CANH_BAO_LICH_SU` + `quy_dinh_hien_hanh_doi_chieu` |
| Mâu thuẫn | `can_cu_mau_thuan`, `FLAG_MAU_THUAN` |
| Sắp hiệu lực | `can_cu_sap_hieu_luc`, `FLAG_VAN_BAN_SAP_HIEU_LUC` |

## Flags trong code (auto)

<!-- BEGIN AUTO-GENERATED:sync_thesis_context.py -->
_Cập nhật lúc 2026-06-15 16:10 UTC_

Trích từ `utils/utils.py` → `chuan_hoa_Context_cho_LLM`:

| Flag trong code | Ý nghĩa (tóm tắt) |
|---|---|
| `FLAG_CANH_BAO_LICH_SU` | Áp dụng luật tại mốc quá khứ |
| `FLAG_CANH_BAO_SUA_DOI` | Có văn bản sửa đổi |
| `FLAG_CANH_BAO_THU_TU_UU_TIEN` | Nhiều cấp bậc pháp lý |
| `FLAG_MAU_THUAN` | Căn cứ mâu thuẫn |
| `FLAG_VAN_BAN_SAP_HIEU_LUC` | Văn bản sắp có hiệu lực |
<!-- END AUTO-GENERATED:sync_thesis_context.py -->
