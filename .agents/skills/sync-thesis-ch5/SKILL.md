---
name: sync-thesis-ch5
description: Đồng bộ Chương 5 đồ án với codebase Agentic GraphRAG. Dùng khi prompt có "đồng bộ chương 5", "sync thesis ch5", hoặc sửa 5_Giai_phap_dong_gop.tex theo code.
---

# Sync Thesis Chapter 5

Đọc đầy đủ `thesis-context/AGENT_WORKFLOW.md` trước khi làm việc.

## Quy trình

1. Đọc `thesis-context/ch05-code-map.md` + label section trong `.tex` cần sửa.
2. Đọc tối đa 3–5 file code được map.
3. So sánh claims trong `.tex` vs code (Neo4j relationships, flags, router).
4. Sửa `.tex`: mô tả + bảng + `\lstinputlisting` ngắn (≤30 dòng).
5. Output checklist khớp/không khớp; ghi mục cần sinh viên duyệt.

## Thứ tự ưu tiên

1. §5.2 legal reasoning (`table:algo_temporal`)
2. KG schema / che_do_tai_san tables
3. Cypher templates (`cypher-template-index.md`)
4. Benchmark (`subsection:benchmark`)
5. Router (optional)

## Ràng buộc

- Chỉ sửa `.tex` trừ khi được yêu cầu sửa code.
- Không bịa tên relationship; dùng `DUOC_SUA_DOI_BOI`, `THAY_THE_BOI`, `HUONG_DAN_BOI`, `BAI_BO_BOI`.
- Không mô tả `adapter/obsolete_retrievers/`.
- Sau sửa lớn: nhắc chạy `scripts/build-thesis.ps1`.

## Prompt templates

Xem `thesis-context/PROMPTS.md` và `thesis-context/SYNC_SESSIONS.md`.
