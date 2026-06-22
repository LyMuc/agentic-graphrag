# Sync Sessions — Chương 5

Mỗi session = **một** subsection. Dùng prompt từ [PROMPTS.md](PROMPTS.md).

## Trạng thái

| # | Subsection | Label | Trạng thái | Ghi chú |
|---|---|---|---|---|
| 1 | Hiệu lực + algo | `table:algo_temporal` | Done | Đồng bộ đủ 5 flags, mâu thuẫn và văn bản sắp hiệu lực |
| 2 | KG văn bản QPPL | `table: Bảng nhãn nút KG` | Done | Đã thêm `BAI_BO_BOI` vào §5.2.2 |
| 3 | Schema che_do_tai_san | `tab:nodes_che_do_tai_san` | Done | Khớp label và relationship trong template tài sản đang dùng |
| 4 | Template phan_loai_tai_san | `alg:phan-loai-seed` | Done | Khớp params, runtime date và quy tắc đối chiếu chung--riêng |
| 5 | Benchmark | `subsection:benchmark` | Done | Giữ nguyên claim phát hiện mâu thuẫn trên 80% |
| 6 | Router | — | Optional | `router.py` + `retriever_catalog.py`; direct tools `clarify/respond/text2cypher`, policy filter đang bypass |
| 7 | Chat guest + memory | — | Optional | `chat-flow.md`, `presentation/main.py`, `presentation/guest_auth.py` |
| 8 | Context merge/dedupe | — | Optional | `application/legal_context.py`, `application/conversation_context.py` |

## Session 1 — Algorithm hiệu lực

**Files code (tối đa 5):**

- `utils/utils.py` (search `chuan_hoa_Context_cho_LLM`)
- `adapter/cypher_templates/chia_tai_san_sau_ly_hon/_common.py`
- `adapter/retrievers/_context_tho_common.py`

**Audit cập nhật (2026-06-15):**

- Code dùng `DUOC_SUA_DOI_BOI` — đồ án §5.2.2 đã liệt kê đúng tên này.
- Năm flags trong code, gồm `FLAG_MAU_THUAN` và `FLAG_VAN_BAN_SAP_HIEU_LUC`, đã được phản ánh trong algorithm.
- Giai đoạn 1 Cypher + Giai đoạn 2 Python tách rõ như algorithm env.

**Prompt Cursor:**

```
@thesis-context/legal-reasoning-flow.md @Chuong/5_Giai_phap_dong_gop.tex
Đồng bộ algorithm (label table:algo_temporal) với legal-reasoning-flow.md.
Chỉ sửa .tex nếu bước nào lệch code; liệt kê diff.
```

## Session 2 — Bảng quan hệ Neo4j

**Files:** `kg-schema.md`, `_context_tho_common.py`, bảng trong `.tex`

**Prompt Codex:**

```
Đối chiếu bảng quan hệ trong 5_Giai_phap_dong_gop.tex với thesis-context/kg-schema.md.
Sửa .tex nếu thiếu BAI_BO_BOI hoặc sai tên quan hệ.
```

## Session 3 — Semantic schema tài sản

**Files:** `adapter/cypher_templates/tai_san/_common.py`, `che_do_tai_san_cua_vo_chong.py`

## Session 4 — Cypher template phan_loai_tai_san

**Files:** `adapter/cypher_templates/tai_san/*.py`, section Template 1 trong `.tex`

## Session 5 — Benchmark

**Files:** `benchmark_dataset/crawl.py`, `benchmark_dataset/benchmark_grouped/*.json`, `benchmark_dataset/scripts/`

## Session 6 — Router (tuỳ chọn)

**Files:** `application/router.py`, `application/retriever_catalog.py`, `application/router_tool_registry.py`, `presentation/main.py`

## Session 7 — Chat guest + conversation memory (tuỳ chọn)

**Files code (tối đa 5):**

- `presentation/main.py`
- `presentation/guest_auth.py`
- `adapter/guest.py`
- `adapter/data_layer.py`
- `application/conversation_context.py`

**Prompt Cursor/Codex:**

```
@thesis-context/chat-flow.md @thesis-context/ch05-code-map.md
Đối chiếu mô tả guest chat và conversation memory với code hiện tại.
Chỉ sửa tài liệu được yêu cầu. Xác nhận guest không persist thread/step/element.
```

## Session 8 — LegalContextBundle và context dedupe (tuỳ chọn)

**Files code (tối đa 5):**

- `application/legal_context.py`
- `application/router.py`
- `application/conversation_context.py`
- `presentation/main.py`
- Một retriever đang import `encode_context_record` nếu cần trích ví dụ.

**Prompt Cursor/Codex:**

```
@thesis-context/chat-flow.md @docs/legal_context_bundle.md
Đối chiếu mô tả LegalContextBundle, process_context_strings và mixed legacy context với code.
Không nói toàn bộ retriever đã migrate sang bundle nếu `rg` còn thấy retriever gọi trực tiếp chuan_hoa_Context_cho_LLM.
```

## Sau mỗi session

1. Chạy `scripts/build-thesis.ps1`
2. Checklist trong `AGENT_WORKFLOW.md`
3. Cập nhật cột Trạng thái bảng trên → `Done`
