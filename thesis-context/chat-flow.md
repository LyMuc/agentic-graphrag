# Chat Flow, guest access và context memory

File này là nguồn đọc nhanh cho agent khi cần mô tả hoặc sửa tài liệu về luồng chat hiện tại sau khi gộp `feature/chat-guest` và `feature/chat-memory-deduplicate`.

## Phạm vi đọc code

Khi task liên quan đến guest chat, lịch sử hội thoại, context memory hoặc dedupe căn cứ pháp lý, chỉ mở các file chính sau trước:

| Chủ đề | File nguồn sự thật |
|---|---|
| Entry Chainlit, session state, Router step metadata | `presentation/main.py` |
| Guest auth API và middleware chặn quản lý hội thoại | `presentation/guest_auth.py` |
| Helper nhận diện guest | `adapter/guest.py` |
| Data layer bỏ qua ghi DB cho guest | `adapter/data_layer.py` |
| Project API và quyền quản lý hội thoại | `presentation/projects_api.py` |
| Router control fields và cache reuse | `application/router.py` |
| Conversation memory, anchor, restore thread | `application/conversation_context.py` |
| LegalContextBundle, merge và render context | `application/legal_context.py` |
| Frontend bootstrap guest và ẩn quản lý hội thoại | `frontend/src/AppWrapper.tsx`, `frontend/src/lib/auth.ts`, `frontend/src/pages/Page.tsx`, `frontend/src/pages/Thread.tsx`, `frontend/src/components/header/UserNav.tsx` |

Tài liệu chi tiết bổ trợ: `docs/conversation_context.md`, `docs/legal_context_bundle.md`.

## Guest chat

Frontend khởi tạo guest ở `frontend/src/AppWrapper.tsx`: khi `useAuth()` đã sẵn sàng, người dùng chưa đăng nhập và không ở `/login` hoặc `/login/callback`, app gọi `ExtendedChainlitAPI.guestAuth()` tới `POST /auth/guest`, rồi gọi `setUserFromAPI()`.

Backend đăng ký ở `presentation/main.py`:

```text
app.middleware("http")(guest_management_guard)
app.include_router(guest_router)
```

`presentation/guest_auth.py` tạo JWT cho user `guest:<uuid>` với metadata `{"auth_mode": "guest", "name": "Guest"}` nếu request chưa có user. Nếu cookie đã là user thật, endpoint không thay thế cookie.

Quyền guest:

- Guest được chat trong phiên hiện tại.
- Guest không có lịch sử hội thoại bền vững trong PostgreSQL.
- Guest không được quản lý conversations/projects/feedback.
- Guest truy cập `/thread/:id` không phải shared route sẽ bị frontend chuyển về `/`.
- Shared/read-only thread vẫn có thể mở qua route share.

`adapter/data_layer.py` dùng `GuestAwareSQLAlchemyDataLayer`: guest có persisted user tổng hợp bằng `uuid5(NAMESPACE_URL, identifier)` nhưng các thao tác `update_thread`, `delete_thread`, `create_step`, `update_step`, `delete_step`, `create_element`, `delete_element` đều trả `None`; feedback raise `PermissionError`. `presentation/projects_api.py` cũng trả 403 cho guest khi quản lý project/thread.

Frontend dùng `canManageConversations(config, user)` trong `frontend/src/lib/auth.ts` để ẩn sidebar lịch sử, share/feedback/quản lý hội thoại cho guest. `UserNav` hiển thị nút Login thay vì avatar khi user là guest.

## Chat lifecycle

`presentation/main.py` là entry backend chính:

```text
on_chat_start
-> reset session_history, retrieval_memory, conversation_anchors
-> gửi greeting

on_chat_resume
-> restore_conversation_state(steps)
-> khôi phục session_history, retrieval_memory, conversation_anchors

on_message
-> build_working_history(...)
-> route_question_with_audit(..., retrieval_memory, thread_id, kg_version)
-> create_retrieval_memory_entries(...)
-> build_turn_anchor(...)
-> process_context_strings(contexts_for_llm)
-> Response LLM stream answer
```

Guest và user thật đều dùng cùng luồng xử lý trong bộ nhớ của Chainlit session. Khác biệt chính là user thật được data layer persist thread/step metadata, còn guest thì không.

## Conversation memory

`application/conversation_context.py` giữ hai lớp lịch sử:

```text
session_history/full_history
  Toàn bộ user + assistant messages trong session hoặc thread đã resume.

working_history
  Một số lượt gần nhất ở dạng đầy đủ + anchor compact của lượt cũ.
```

Các biến môi trường điều chỉnh budget:

```text
RECENT_FULL_TURNS=4
ROUTER_HISTORY_MAX_TOKENS=3000
RESPONSE_HISTORY_MAX_TOKENS=4000
OLDER_TURN_INDEX_LIMIT=20
KG_VERSION=<optional>
```

`build_working_history` dùng token estimator cục bộ, không gọi API tóm tắt lịch sử. Router giữ nguyên văn câu hỏi user cho retriever, chỉ resolve pronoun/ellipsis khi follow-up.

Một `retrieval_memory` entry gồm:

```json
{
  "context_ref": "uuid",
  "turn_id": "uuid",
  "thread_id": "chainlit-thread-id",
  "retriever_name": "dieu_kien_ket_hon",
  "resolved_query": "câu hỏi gửi retriever (nguyên văn hoặc đã resolve pronoun)",
  "encoded_contexts": ["LEGAL_CONTEXT_BUNDLE_V1:..."],
  "target_dates": ["2026-06-21"],
  "kg_version": "2026-06-21.1",
  "created_at": "..."
}
```

Nếu `KG_VERSION` không được cấu hình, `current_kg_version()` dùng version riêng cho process, nên cache không an toàn qua restart.

## Router cache reuse

`application/router.py` thêm metadata/field điều khiển cho mọi retriever không phải direct tool:

```json
{
  "confidence_score": 0.86,
  "context_action": "retrieve | reuse",
  "context_refs": ["..."],
  "time_scope": "current | explicit | ambiguous",
  "target_date": "YYYY-MM-DD hoặc YYYY"
}
```

Các field này bị loại khỏi args trước khi gọi retriever. Router chỉ nên đặt `context_action="reuse"` khi context cũ cùng retriever, cùng mốc thời gian và câu follow-up không mở thêm vấn đề pháp lý mới.

**Chính sách `query`:** mặc định truyền nguyên văn toàn bộ câu hỏi user cho mọi retriever (cùng một `query` khi gọi nhiều retriever). Chỉ resolve pronoun/ellipsis khi follow-up (ví dụ "Còn nữ thì sao?", "anh ấy", "cái đó"); không paraphrase, không tóm tắt, không tách sub-question theo retriever.

Direct tool hiện tại: `clarify`, `respond`. Trong đó `clarify` và `respond` là phản hồi trực tiếp/exclusive: nếu Router chọn một trong hai thì không chạy thêm retriever; `clarify` chỉ dùng khi follow-up còn từ hai cách hiểu hợp lý trở lên sau khi xét lịch sử gần và anchor.

Lưu ý trạng thái code hiện tại: package `retriever_policy/` (`evaluate_retriever_policy`, `evaluate_tool_calls_policy`) vẫn tồn tại cho test/benchmark, nhưng `route_question_with_audit` trong luồng chính không gọi policy filter và chấp nhận các tool call đã loại trùng từ Router LLM. Vì vậy khi viết đồ án, không mô tả `RetrieverPolicy` là cổng lọc bắt buộc của production flow.

`validate_reuse_request` kiểm tra quyết định reuse bằng luật deterministic:

- `context_ref` phải tồn tại trong memory của đúng `thread_id`.
- `retriever_name` phải trùng tool đang gọi.
- `kg_version` phải trùng.
- `target_date` và `is_user_provided_date` của bundle phải trùng kỳ vọng từ `time_scope`.
- Encoded bundle phải parse được và merge được bằng `process_context_strings`.

Nếu pass, `_reuse_tool_call` trả kết quả giống retriever với `cache_status="reused"` và `context_refs_used`. Nếu fail, Router fallback sang gọi retriever thật và ghi `cache_fallback_reason`.

## LegalContextBundle và dedupe context

`application/legal_context.py` là lớp gom nhiều context thành một prompt pháp lý duy nhất.

Luồng bundle:

```text
Context_Tho từ Neo4j
-> build_legal_context_bundle
-> encode_legal_context_bundle
-> contexts của retriever
-> process_context_strings
-> group theo (target_date, is_user_provided_date)
-> merge_legal_context_bundles
-> render_legal_context_bundle
-> chuan_hoa_Context_cho_LLM
```

Khóa dedupe provision:

```text
id + amendment_id + effective_from + effective_until
```

Ưu tiên role:

```text
main > guidance > support
```

Quan hệ hướng dẫn, tương lai, mâu thuẫn, replacement IDs và citation links được dedupe riêng. Provenance retriever/template được giữ lại khi merge.

Trạng thái migration hiện tại là mixed-compatible:

- Retriever đã import `encode_context_record` trả `LEGAL_CONTEXT_BUNDLE_V1:...`, dedupe được trên provision giữa nhiều template/retriever.
- Retriever còn gọi trực tiếp `chuan_hoa_Context_cho_LLM` trả legacy text; `process_context_strings` giữ nguyên text đó và nối sau phần bundle, không cam kết dedupe giữa legacy text và bundle.
- Khi viết đồ án, không mô tả rằng mọi retriever đã migrate sang bundle nếu code chưa cho thấy điều đó. Kiểm tra nhanh bằng `rg "encode_context_record|chuan_hoa_Context_cho_LLM" adapter/retrievers`.

## Metadata và quan sát trong UI

Router/assistant step metadata hiện đáng chú ý:

- Không có `router_policy` trong production path vì policy filter đang bị comment và `route_question_with_audit` trả `None`.
- `tool_response[*].cache_status`: `retrieved` hoặc `reused`
- `tool_response[*].cache_fallback_reason`
- `retrieval_memory_entries`
- `turn_anchor`
- `kg_version`

Trong expert mode:

- `Retriever: <name>` nghĩa là retriever thật đã chạy.
- `Retriever cache: <name>` nghĩa là đã reuse context từ memory.
- `Luồng truy xuất ngữ cảnh` bao quanh Router và retriever steps.
- `Tổng hợp đáp án` là Response LLM step, không xuất hiện khi direct `clarify` hoặc `respond`.

## Test liên quan

Backend:

- `tests/test_guest_access.py`
- `tests/test_conversation_context.py`
- `tests/test_router_conversation.py`
- `tests/test_legal_context.py`
- `scripts/test_context_dedupe.py`

Frontend:

- `frontend/tests/auth.spec.ts`
- `frontend/tests/UserNav.spec.tsx`
