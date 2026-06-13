# Sync Sessions — Chương 5

Mỗi session = **một** subsection. Dùng prompt từ [PROMPTS.md](PROMPTS.md).

## Trạng thái

| # | Subsection | Label | Trạng thái | Ghi chú |
|---|---|---|---|---|
| 1 | Hiệu lực + algo | `table:algo_temporal` | Ready | Map: `legal-reasoning-flow.md` |
| 2 | KG văn bản QPPL | `table: Bảng nhãn nút KG` | Done | Đã thêm `BAI_BO_BOI` vào §5.2.2 |
| 3 | Schema che_do_tai_san | `tab:nodes_che_do_tai_san` | Ready | `tai_san/_common.py` |
| 4 | Template phan_loai_tai_san | `alg:phan-loai-seed` | Ready | `cypher_templates/tai_san/` |
| 5 | Benchmark | `subsection:benchmark` | Ready | `benchmark_dataset/` |
| 6 | Router | — | Optional | `router.py` + `retriever_catalog.py` |

## Session 1 — Algorithm hiệu lực

**Files code (tối đa 5):**

- `utils/utils.py` (search `chuan_hoa_Context_cho_LLM`)
- `adapter/cypher_templates/chia_tai_san_sau_ly_hon/_common.py`
- `adapter/retrievers/_context_tho_common.py`

**Audit đã thực hiện khi setup (2026-06-13):**

- Code dùng `DUOC_SUA_DOI_BOI` — đồ án §5.2.2 đã liệt kê đúng tên này.
- Flags trong code: `FLAG_CANH_BAO_*` khớp mô tả `legal-reasoning-flow.md`.
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

**Files:** `application/router.py`, `application/retriever_catalog.py`, `presentation/main.py`

## Sau mỗi session

1. Chạy `scripts/build-thesis.ps1`
2. Checklist trong `AGENT_WORKFLOW.md`
3. Cập nhật cột Trạng thái bảng trên → `Done`
