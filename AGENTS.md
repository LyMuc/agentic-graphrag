# Agentic GraphRAG Chatbot Luật

## Trước khi sửa nội dung kỹ thuật trong đồ án

1. Đọc `thesis-context/AGENT_WORKFLOW.md` (quy trình đầy đủ).
2. Đọc `thesis-context/ch05-code-map.md` (map section → file code) và `thesis-context/server-architecture.md` (kiến trúc cây `server/`).
3. Nếu sửa/mô tả guest chat, context memory, cache reuse hoặc dedupe căn cứ pháp lý, đọc thêm `thesis-context/chat-flow.md`.
4. Chỉ mở file code được map; không quét `data/`, `extraction/`, `adapter/obsolete_retrievers/`.

> Code đã refactor vào cây `server/` (xem `server-architecture.md`). Các path cũ
> `presentation/`, `application/`, `adapter/`, `utils/` chỉ còn là shim back-compat
> (re-export sang `server.*`) — ưu tiên đọc/sửa ở `server/`.

## Ưu tiên

- Code thực tế > mô tả cũ trong `.tex` nếu lệch nhau.
- Chỉ sửa `.tex` khi được yêu cầu viết đồ án; không refactor codebase trừ khi được yêu cầu.
- Với flow chat hiện tại: Router dùng `build_working_history`, `retrieval_memory`, `context_action/context_refs` và `LegalContextBundle`.
- Guest chat dùng JWT `guest:<uuid>` và không persist thread/step/element vào PostgreSQL.

## LaTeX

- Root: `ĐATN_20225919_Lê_Thái_Sơn_Chatbot_tư_vấn_luật_hôn_nhân_gia_đình/DoAn.tex`
- Build output: `ĐATN_.../build/DoAn.pdf`
- Build: `powershell -File scripts/build-thesis.ps1`
- Sync context: `powershell -File scripts/sync-thesis-context.ps1` (catalog, templates, KG rels — không sửa `.tex`)
- Chat flow context: `thesis-context/chat-flow.md`
- Chèn code bằng `\lstinputlisting`; giữ format UET/ĐATN.
- LaTeX Workshop: recipe `pdflatex` (không dùng latexmk — path Unicode Windows).

## Skills

- Đồng bộ Chương 5: skill `sync-thesis-ch5` (`.agents/skills/`)
