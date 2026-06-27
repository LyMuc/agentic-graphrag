# Agent Workflow — Viết đồ án khớp codebase

Nguồn sự thật cho Cursor Agent, Codex (VS Code), và mọi prompt. Cập nhật file này trước khi sửa `.cursor/rules/`, `.cursor/skills/`, `.agents/skills/`.

## Quy trình 5 bước (bắt buộc)

1. Đọc `thesis-context/ch05-code-map.md` + label `\section`/`\subsection` cần sửa trong `.tex`. Nếu task liên quan guest chat, session memory, cache reuse hoặc dedupe context, đọc thêm `thesis-context/chat-flow.md`.
2. Đọc **tối đa 3–5 file code** được map (không quét toàn repo).
3. So sánh mô tả trong `.tex` vs code (tên quan hệ Neo4j, flags, luồng router).
4. Sửa `.tex`: mô tả + bảng/pseudocode + `\lstinputlisting` ngắn (≤30 dòng) khi cần trích code.
5. Liệt kê mục đã đồng bộ và mục cần sinh viên xác nhận (hình vẽ, số liệu benchmark).

## Quy tắc LaTeX (UET/ĐATN)

- Root: `ĐATN_20225919_Lê_Thái_Sơn_Chatbot_tư_vấn_luật_hôn_nhân_gia_đình/DoAn.tex`.
- Chương con dùng `subfiles`; **không** đổi preamble `DoAn.tex` trừ khi được yêu cầu.
- Giữ `\section`, `\subsection`, `\cite{}`, `\ref{}` nhất quán với label hiện có.
- Chèn code bằng `\lstinputlisting` (cấu hình trong `lstlisting.tex`); tránh inline dài.
- Build: `scripts/build-thesis.ps1` hoặc LaTeX Workshop (recipe `pdflatex`, **không** `latexmk` — tránh lỗi path Unicode trên Windows).
- Output PDF: `ĐATN_.../build/DoAn.pdf`.

## Quy trình đồng bộ code

- **Code thực tế > mô tả cũ** trong `.tex` nếu lệch nhau.
- Toàn bộ retriever đang sử dụng nằm trong `adapter/retrievers/`; không gắn nhãn phiên bản cho kiến trúc retriever.
- **Catalog / template / quan hệ / flags:** chạy `powershell -File scripts/sync-thesis-context.ps1` — không cập nhật tay các bảng AUTO trong `thesis-context/`.
- **Chương 5 (.tex):** vẫn cần agent hoặc sinh viên (skill `sync-thesis-ch5`) — script không sửa LaTeX.
- Chỉ sửa `.tex` khi nhiệm vụ là viết đồ án; không refactor codebase trừ khi được yêu cầu.
- **Guest/chat memory/context dedupe:** đọc `chat-flow.md` trước; flow hiện tại dùng `retrieval_memory`, `conversation_anchors`, Router `confidence_score/context_action/context_refs` và `LegalContextBundle`.
- **Không bịa** tên module, relationship Neo4j, flags — chỉ dùng tên có trong code hoặc `kg-schema.md`.
- **Không** mô tả retriever trong `adapter/obsolete_retrievers/` (trừ khi ghi rõ legacy).
- Thư mục **không** quét: `data/`, `extraction/`, `benchmark_dataset/benchmark/`, `public/chainlit-build/`.

## Quan hệ Neo4j chuẩn (legal layer)

Bảng đầy đủ (auto): `kg-schema.md`. Tóm tắt thường dùng:

| Quan hệ | Ý nghĩa |
|---|---|
| `CO_DIEU`, `CO_KHOAN`, `CO_DIEM` | Cấu trúc văn bản |
| `THAM_CHIEU_DEN` | Tham chiếu bổ trợ |
| `DUOC_SUA_DOI_BOI` | Sửa đổi (không dùng `SUA_DOI_BOI`) |
| `HUONG_DAN_BOI` | Hướng dẫn |
| `THAY_THE_BOI` | Thay thế (moi/cu) |
| `BAI_BO_BOI` | Bãi bỏ / sắp hiệu lực |

## Luồng chat hiện tại

Nguồn tóm tắt: `chat-flow.md`.

- Guest chat: frontend gọi `/auth/guest`, backend tạo JWT `guest:<uuid>`, data layer không persist thread/step/element cho guest.
- Conversation memory: `presentation/main.py` giữ `session_history`, `retrieval_memory`, `conversation_anchors`; resume thread đọc lại metadata bằng `restore_conversation_state`.
- Router: mỗi retriever có metadata/control fields `confidence_score`, `context_action`, `context_refs`, `time_scope`, `target_date`; reuse phải qua `validate_reuse_request`.
- Direct tool: `clarify`, `respond`; `clarify` và `respond` là phản hồi trực tiếp/exclusive.
- `RetrieverPolicy` hiện là helper/test/benchmark; luồng chính trong `route_question_with_audit` đang bỏ qua policy filter.
- Context merge/dedupe: `application/legal_context.py` xử lý `LEGAL_CONTEXT_BUNDLE_V1` theo `(target_date, is_user_provided_date)`, dedupe provision theo `id + amendment_id + effective_from + effective_until`, rồi render bằng `chuan_hoa_Context_cho_LLM`.
- Trạng thái migration: một số retriever vẫn trả legacy text từ `chuan_hoa_Context_cho_LLM`; `process_context_strings` nối legacy nguyên văn và chỉ dedupe mạnh cho bundle.

## Flags chuẩn hóa context

Bảng auto: `legal-reasoning-flow.md` (khối AUTO). Hàm: `utils/utils.py` → `chuan_hoa_Context_cho_LLM`.

Thuật toán trong `algorithm` env (label `table:algo_temporal`) tương ứng pipeline: Cypher `EXPAND_AND_TIMEFILTER` trong `adapter/cypher_templates/*/_common.py` → `Context_Tho` → `chuan_hoa_Context_cho_LLM`.

## Chương 5 — thứ tự session đồng bộ

1. §5.2 — Legal reasoning + KG schema (`subsection:5.2.2`, `table:algo_temporal`)
2. Schema/template theo domain (`che_do_tai_san`, `phan_loai_tai_san`, …)
3. Benchmark (`subsection:benchmark`)
4. Router (nếu mở rộng sang chương khác: `application/router.py`)

Chi tiết map: `ch05-code-map.md`. Prompt mẫu: `PROMPTS.md`, `SYNC_SESSIONS.md`.

## Checklist sau mỗi lần sửa

- [ ] Đã chạy `scripts/sync-thesis-context.ps1` nếu đổi retriever/template/KG flags
- [ ] Tên quan hệ Neo4j khớp code
- [ ] Thuật toán khớp thứ tự bước trong `_common.py` + `chuan_hoa_Context_cho_LLM`
- [ ] `\lstinputlisting` compile được
- [ ] Không cite obsolete retriever
- [ ] `\ref{}` / `\cite{}` resolve sau build
- [ ] `scripts/build-thesis.ps1` pass
