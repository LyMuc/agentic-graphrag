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
  → LegalContextBundle nếu retriever đã migrate, hoặc legacy rendered text
  → process_context_strings (application/legal_context.py)
       • merge/dedupe bundle theo temporal scope
       • nối legacy text nguyên văn
  → chuan_hoa_Context_cho_LLM (utils/utils.py) khi render bundle
  → Response LLM (presentation/main.py main_prompt)
```

Chi tiết flow chat, retrieval cache và trạng thái mixed-compatible nằm trong
`thesis-context/chat-flow.md`.

## Giai đoạn 1 — Truy xuất trên đồ thị (Cypher)

Implement trong `adapter/cypher_templates/*/_common.py`, dùng snippet chung từ
`adapter/retrievers/_context_tho_common.py`:

1. Match seed điều/khoản/điểm (từ IDs hoặc semantic graph).
2. Expand cấu trúc (`CO_KHOAN`, `CO_DIEM`) và heading cha.
3. `THAY_THE_BOI` có hướng (moi/cu) — lọc theo `$target_date`.
4. `DUOC_SUA_DOI_BOI`, `HUONG_DAN_BOI`, mở rộng chi tiết hướng dẫn.
5. `THAM_CHIEU_DEN` / ancestor collect (`_context_tho_common.py`).
6. `quy_dinh_hien_hanh_doi_chieu` — văn bản thay thế đã có hiệu lực tại `$query_date` (ngày đặt câu hỏi).
7. `lien_ket_hien_hanh` — cặp `(id_hien_hanh, id_duoc_thay_the)` cho từng quan hệ thay thế hiện hành.
8. `can_cu_sap_hieu_luc` — văn bản chưa có hiệu lực tại `$query_date`; `$target_date` chỉ lọc căn cứ áp dụng theo mốc sự kiện.

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
_Cập nhật lúc 2026-06-17 14:54 UTC_

Trích từ `utils/utils.py` → `chuan_hoa_Context_cho_LLM`:

| Flag trong code | Ý nghĩa (tóm tắt) |
|---|---|
| `FLAG_CANH_BAO_LICH_SU` | Áp dụng luật tại mốc quá khứ |
| `FLAG_CANH_BAO_SUA_DOI` | Có văn bản sửa đổi |
| `FLAG_CANH_BAO_THU_TU_UU_TIEN` | Nhiều cấp bậc pháp lý |
| `FLAG_MAU_THUAN` | Căn cứ mâu thuẫn |
| `FLAG_VAN_BAN_SAP_HIEU_LUC` | Văn bản sắp có hiệu lực |
<!-- END AUTO-GENERATED:sync_thesis_context.py -->
