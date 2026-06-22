# Thesis Context Index

Thư mục ngữ cảnh dùng chung cho **Cursor Agent** và **Codex (VS Code)**. Luôn `@` file này hoặc `AGENT_WORKFLOW.md` trước khi sửa đồ án.

## Tự động vs thủ công

**Không cần** cập nhật tay toàn bộ `thesis-context/` mỗi lần đổi code.

| Loại | File | Cách cập nhật |
|---|---|---|
| **Tự động** | `retriever-catalog.md`, `cypher-template-index.md`, phần quan hệ trong `kg-schema.md`, phần flags trong `legal-reasoning-flow.md` | `powershell -File scripts/sync-thesis-context.ps1` |
| **Thủ công** | `AGENT_WORKFLOW.md`, `ch05-code-map.md`, `architecture.md`, `chat-flow.md`, `PROMPTS.md`, `SYNC_SESSIONS.md` | Agent/sinh viên khi đổi kiến trúc hoặc viết Chương 4/5 |
| **LaTeX** | `ĐATN_.../Chuong/*.tex` | Skill `sync-thesis-ch5` sau khi chạy sync script |

Khối giữa `<!-- BEGIN AUTO-GENERATED -->` … `<!-- END AUTO-GENERATED -->` bị ghi đè khi chạy sync — **không sửa tay** trong khối đó.

## Mục lục file

| File | Mục đích |
|---|---|
| [AGENT_WORKFLOW.md](AGENT_WORKFLOW.md) | Quy trình, quy tắc LaTeX, flags, checklist |
| [ch05-code-map.md](ch05-code-map.md) | Map Chương 5 → file code (ưu tiên) |
| [PROMPTS.md](PROMPTS.md) | Prompt mẫu Cursor + Codex |
| [SYNC_SESSIONS.md](SYNC_SESSIONS.md) | Lịch session đồng bộ Chương 5 |
| [architecture.md](architecture.md) | Kiến trúc hệ thống (tóm tắt) |
| [chat-flow.md](chat-flow.md) | Guest chat, conversation memory, cache reuse, LegalContextBundle |
| [retriever-catalog.md](retriever-catalog.md) | Tool → file Python |
| [kg-schema.md](kg-schema.md) | Node/relationship Neo4j |
| [cypher-template-index.md](cypher-template-index.md) | Template theo domain |
| [legal-reasoning-flow.md](legal-reasoning-flow.md) | Pipeline Context_Tho → LLM |

## LaTeX build

```powershell
powershell -File scripts/build-thesis.ps1
```

## Đồng bộ thesis-context ↔ code

```powershell
powershell -File scripts/sync-thesis-context.ps1
```

Chạy sau khi thêm/sửa retriever, template Cypher, quan hệ Neo4j trong `_context_tho_common.py`, hoặc flags trong `chuan_hoa_Context_cho_LLM`. Sau đó mới nhờ agent đồng bộ `.tex` (Chương 5).

PDF: `ĐATN_20225919_Lê_Thái_Sơn_Chatbot_tư_vấn_luật_hôn_nhân_gia_đình/build/DoAn.pdf`

## Changelog đồng bộ thesis ↔ code

| Ngày | Mục | Ghi chú |
|---|---|---|
| 2026-06-13 | Setup | Tạo thesis-context, AGENTS.md, rules, skills; build PDF 80 trang OK |
| 2026-06-13 | §5.2.2 KG | Thêm quan hệ `BAI_BO_BOI` vào mô tả (khớp `_context_tho_common.py`) |
| 2026-06-13 | Sync script | `scripts/sync_thesis_context.py` — auto catalog/registry/KG rels/flags |
| 2026-06-15 | 20 retrievers | Sync catalog + registry; xác nhận retriever đang dùng nằm trong `adapter/retrievers/` và đủ 20 domain |
| 2026-06-21 | Guest + context memory | Thêm map cho guest chat, `retrieval_memory`, Router `context_action/context_refs`, `LegalContextBundle` và mixed legacy context |
| 2026-06-23 | Router direct tools | Sync direct tool `clarify`, `confidence_score` và trạng thái policy filter đang bypass trong luồng chính |

## Tham chiếu repo

- Code entry: `presentation/main.py`
- Router: `application/router.py`
- Chat flow hiện tại: `thesis-context/chat-flow.md`
- Đồ án Chương 5: `ĐATN_.../Chuong/5_Giai_phap_dong_gop.tex`
