# Kiến trúc hệ thống (tóm tắt)

Rút gọn từ [integration.md](../integration.md) và [README.md](../README.md).

## Luồng một câu hỏi

```text
Người dùng (frontend Chainlit)
    → nếu chưa đăng nhập: POST /auth/guest tạo JWT guest
    → presentation/main.py
    → build_working_history(session_history + conversation_anchors)
    → application/router.py (Router LLM chọn tool + context_action)
    → reuse retrieval_memory hoặc gọi adapter/retrievers/*
    → application/legal_context.py (process_context_strings, merge/dedupe)
    → utils/utils.py (chuan_hoa_Context_cho_LLM khi render)
    → Response LLM stream câu trả lời
```

## Lớp phần mềm (server)

| Lớp | Thư mục | Vai trò |
|---|---|---|
| Frontend | `frontend/src/` | Chainlit UI, bootstrap guest, ẩn quản lý hội thoại cho guest |
| Presentation | `presentation/` | Chainlit hooks, registry tools, OAuth/guest auth, project API |
| Application | `application/` | Router, retriever catalog, policy helper/benchmark, conversation memory, legal context bundle |
| Adapter | `adapter/` | Neo4j/LLM config, retrievers, cypher templates |
| Utils | `utils/` | Chuẩn hóa context, tiện ích |

## Dữ liệu

- **Neo4j**: đồ thị pháp luật + KG ngữ nghĩa theo topic (semantic nodes + `CAN_CU_TAI`).
- **PostgreSQL**: Chainlit threads/steps (chỉ bền vững cho user đăng nhập thật).
- **Guest session**: user `guest:<uuid>` dùng JWT và bộ nhớ Chainlit session, không persist thread/step/element vào PostgreSQL.
- **Vercel AI Gateway**: Router / Retriever / Response LLM.

## Agentic GraphRAG

- Router chọn **một hoặc nhiều** retriever (**20** domain), chạy **song song**.
- Toàn bộ retriever đang sử dụng nằm trong `adapter/retrievers/`.
- Mỗi retriever phân loại một hoặc nhiều Cypher template, trích xuất params cùng `thoi_diem_su_kien`, thực thi Neo4j và trả `Context_Tho`.
- Router schema hiện có thêm `confidence_score`, `context_action`, `context_refs`, `time_scope`, `target_date` cho retriever; các field điều khiển bị loại trước khi gọi function thật.
- Direct tool gồm `clarify`, `respond`; `clarify` và `respond` là phản hồi trực tiếp/exclusive.
- Luồng chính hiện bỏ qua `RetrieverPolicy` filter trong `route_question_with_audit`; policy helper vẫn còn cho test/benchmark và tham khảo.
- `retrieval_memory` lưu các `LegalContextBundle` đã encode theo `context_ref`; reuse chỉ được chấp nhận sau kiểm tra deterministic về thread, retriever, KG version và temporal scope.
- Context từ nhiều retriever được đưa qua `process_context_strings` để merge/dedupe bundle theo căn cứ pháp lý trước khi render cho Response LLM.
- Migration context đang ở trạng thái mixed-compatible: retriever dùng `encode_context_record` trả `LEGAL_CONTEXT_BUNDLE_V1`, retriever còn gọi `chuan_hoa_Context_cho_LLM` trả legacy text và được nối nguyên văn.

## Guest chat và quản lý hội thoại

- `frontend/src/AppWrapper.tsx` tự gọi `/auth/guest` khi người dùng chưa đăng nhập và không ở trang login.
- `presentation/guest_auth.py` tạo JWT guest nhưng không thay thế cookie của user thật.
- `adapter/data_layer.py` trả synthetic persisted guest và bỏ qua ghi thread/step/element cho guest.
- `presentation/projects_api.py` và `guest_management_guard` trả 403 cho các API quản lý project/thread/feedback của guest.
- Frontend dùng `canManageConversations` để ẩn sidebar lịch sử, share/feedback và chuyển guest khỏi route `/thread/:id`.

Chi tiết luồng: [chat-flow.md](chat-flow.md).

## Liên hệ đồ án

- Chương 4: kiến trúc client–server, package diagram, Agentic workflow.
- Chương 5: legal reasoning, Cypher templates, context merge/dedupe, benchmark.
