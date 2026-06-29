# Kiến trúc hệ thống (tóm tắt)

Rút gọn từ [integration.md](../integration.md) và [README.md](../README.md).
Kiến trúc đích chi tiết (Router + Subagents + ConversationOrchestrator):
[server-architecture.md](server-architecture.md).

## Luồng một câu hỏi

```text
Người dùng (frontend Chainlit)
    → nếu chưa đăng nhập: POST /auth/guest tạo JWT guest
    → server/app/main.py (Chainlit hooks) → ConversationOrchestrator.on_message
    → build_working_history(session_history + conversation_anchors)
    → RouterAgent (server/agents/router/) — Router LLM chọn tool + context_action
    → reuse retrieval_memory hoặc fan-out song song server/agents/retrievers/*
    → server/domain/legal/bundle.py (process_context_strings, merge/dedupe)
    → server/domain/legal/render.py (chuan_hoa_Context_cho_LLM khi render)
    → SynthesizerAgent (server/agents/synthesizer/) — Response LLM stream câu trả lời
```

## Lớp phần mềm (server, cây `server/`)

| Lớp | Thư mục | Vai trò |
|---|---|---|
| Frontend | `frontend/src/` | Chainlit UI, bootstrap guest, ẩn quản lý hội thoại cho guest |
| App | `server/app/` | Chainlit hooks (`main.py`) + FastAPI routes (`routes/guest_auth.py`, `projects.py`, `viz.py`) |
| Conversation | `server/conversation/` | `ConversationOrchestrator` (stateful, **không LLM**), `memory.py`, `history.py` |
| Agents | `server/agents/` | `RouterAgent`, 20 `RetrieverAgent`, `SynthesizerAgent`, direct (`respond`/`clarify`) — **LLM-driven** |
| Domain | `server/domain/legal/` | Kiểu pháp lý thuần: `bundle`, `codec`, `render`, `warnings` |
| Infrastructure | `server/infrastructure/` | `llm/factory`, `neo4j/{client,cypher_templates}`, `persistence/{data_layer,projects,guest}`, `viz/` |
| Interface | `server/interface/` | Tool schema OpenAI cho Router LLM (`router_tools.py`) |
| Shared | `server/shared/` | `phrase_match`, `datetime_vn`, `llm_text` |

> Các path cũ (`presentation/`, `application/`, `adapter/`, `utils/`) vẫn còn dưới
> dạng **shim back-compat** (re-export sang `server.*`) cho tới khi gỡ ở PR riêng.

## Dữ liệu

- **Neo4j**: đồ thị pháp luật + KG ngữ nghĩa theo topic (semantic nodes + `CAN_CU_TAI`).
- **PostgreSQL**: Chainlit threads/steps (chỉ bền vững cho user đăng nhập thật).
- **Guest session**: user `guest:<uuid>` dùng JWT và bộ nhớ Chainlit session, không persist thread/step/element vào PostgreSQL.
- **OpenAI API**: Router / Retriever / Response LLM (`server/infrastructure/llm/factory.py`).

## Agentic GraphRAG (Router + Subagents pattern)

- `ConversationOrchestrator` (deterministic, không LLM) bọc Router stateless theo biến thể *external state management*.
- `RouterAgent` chọn **một hoặc nhiều** retriever (**20** domain), chạy **song song** (`asyncio.gather`).
- Toàn bộ retriever đang sử dụng nằm trong `server/agents/retrievers/` (mỗi file là một `RetrieverAgent`).
- Mỗi retriever phân loại một hoặc nhiều Cypher template, trích xuất params cùng `thoi_diem_su_kien`, thực thi Neo4j và trả `Context_Tho`.
- Router schema hiện có thêm `confidence_score`, `context_action`, `context_refs`, `time_scope`, `target_date` cho retriever; các field điều khiển bị loại trước khi gọi function thật.
- Direct tool gồm `clarify`, `respond`; `clarify` và `respond` là phản hồi trực tiếp/exclusive.
- Luồng chat production không gọi `RetrieverPolicy`; package `retriever_policy/` ở repo root vẫn phục vụ test/benchmark.
- `retrieval_memory` lưu các `LegalContextBundle` đã encode theo `context_ref`; reuse chỉ được chấp nhận sau kiểm tra deterministic về thread, retriever, KG version và temporal scope.
- Context từ nhiều retriever được đưa qua `process_context_strings` để merge/dedupe bundle theo căn cứ pháp lý trước khi render cho Response LLM.
- Migration context đang ở trạng thái mixed-compatible: retriever dùng `encode_context_record` trả `LEGAL_CONTEXT_BUNDLE_V1`, retriever còn gọi `chuan_hoa_Context_cho_LLM` trả legacy text và được nối nguyên văn.

## Guest chat và quản lý hội thoại

- `frontend/src/AppWrapper.tsx` tự gọi `/auth/guest` khi người dùng chưa đăng nhập và không ở trang login.
- `server/app/routes/guest_auth.py` tạo JWT guest nhưng không thay thế cookie của user thật.
- `server/infrastructure/persistence/data_layer.py` trả synthetic persisted guest và bỏ qua ghi thread/step/element cho guest.
- `server/app/routes/projects.py` và `guest_management_guard` trả 403 cho các API quản lý project/thread/feedback của guest.
- Frontend dùng `canManageConversations` để ẩn sidebar lịch sử, share/feedback và chuyển guest khỏi route `/thread/:id`.

Chi tiết luồng: [chat-flow.md](chat-flow.md).

## Liên hệ đồ án

- Chương 4: kiến trúc client–server, package diagram, Agentic workflow.
- Chương 5: legal reasoning, Cypher templates, context merge/dedupe, benchmark.
