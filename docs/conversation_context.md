# Context hội thoại, follow-up và retrieval cache

## Luồng tổng quát

Hệ thống giữ hai lớp lịch sử:

```text
session_history/full_history
  Toàn bộ user + assistant messages, phục vụ UI và audit.

working_history
  Các lượt gần nhất đầy đủ + anchor của lượt cũ, bị giới hạn token.
```

Mỗi lượt:

```text
User message
→ build_working_history
→ Router LLM hiện có
→ resolved query + tool + cache controls
→ RetrieverPolicy trên resolved query
→ deterministic reuse validation
→ reuse hoặc gọi retriever
→ merge context bằng LegalContextBundle
→ Response LLM hoặc direct clarify/respond
```

Không có Query Updater và không có lượt LLM tóm tắt lịch sử.

## Router control fields

Mỗi retriever tool có các field tùy chọn:

```json
{
  "query": "Câu hỏi độc lập đã giải nghĩa",
  "context_action": "retrieve | reuse",
  "context_refs": ["..."],
  "time_scope": "current | explicit | ambiguous",
  "target_date": "YYYY-MM-DD hoặc YYYY"
}
```

Control fields bị loại trước khi gọi retriever. Retriever chỉ nhận `query` và
các business argument vốn có.

## Retrieval memory

Một entry được persist trong metadata của Router step:

```json
{
  "context_ref": "uuid",
  "turn_id": "uuid",
  "thread_id": "chainlit-thread-id",
  "retriever_name": "dieu_kien_ket_hon",
  "resolved_query": "Nam 18 tuổi có đủ điều kiện kết hôn không?",
  "encoded_contexts": ["LEGAL_CONTEXT_BUNDLE_V1:..."],
  "target_dates": ["2026-06-11"],
  "kg_version": "2026-06-11.1",
  "created_at": "..."
}
```

Resume thread đọc `retrieval_memory_entries` và `turn_anchor` từ metadata. Thread
cũ không có các field này vẫn phục hồi messages và tiếp tục retrieve bình
thường.

## Kịch bản kiểm thử

### 1. Follow-up từ lịch sử gần

User messages:

```text
U1: Nam 18 tuổi có được kết hôn không?
U2: Còn nữ thì sao?
```

Working history:

```text
U1 + câu trả lời A1 đầy đủ
```

Router decision:

```json
{
  "tool": "dieu_kien_ket_hon",
  "query": "Nữ 18 tuổi có đủ điều kiện kết hôn không?",
  "context_action": "reuse",
  "context_refs": ["ctx-u1"],
  "time_scope": "current"
}
```

Deterministic validation:

```text
thread đúng
retriever đúng
target_date là hôm nay
KG_VERSION đúng
bundle hợp lệ
→ accepted
```

Retriever calls: `0`.

Merged context: bundle Điều 8 từ `ctx-u1`.

Final response path: Router → cache → Response LLM.

### 2. Follow-up từ anchor cũ

User messages:

```text
U1: Tôi mua căn nhà trước khi kết hôn.
U2..U14: Trao đổi về con và cấp dưỡng.
U15: Nếu tôi bán căn nhà đó thì có cần chữ ký của chồng không?
```

Working history:

```text
system anchor:
turn-1 | resolved_query=Quyền đối với căn nhà mua trước hôn nhân
       | retrievers=che_do_tai_san_cua_vo_chong
       | context_refs=ctx-house

4 lượt gần nhất đầy đủ
```

Router giải được đối tượng “căn nhà đó” từ anchor. Router có thể chọn reuse nếu
context cũ bao phủ quyền định đoạt; nếu context cũ chỉ bao phủ phân loại tài sản,
Router chọn retrieve cùng retriever với resolved query mới.

### 3. Reuse thành công

Router decision:

```text
context_action=reuse
context_refs=ctx-1
```

Các API bị bỏ qua:

```text
Retriever LLM classify/extract: không gọi
Neo4j retrieval query: không gọi
```

Response LLM vẫn được gọi để trả lời follow-up, vì câu trả lời mới có thể cần
diễn giải khác dù căn cứ giống nhau.

Chainlit hiển thị step:

```text
Retriever cache: dieu_kien_ket_hon
Context cache reused.
Refs: ctx-1
```

### 4. Tình tiết mới buộc retrieve

User messages:

```text
U1: Nhà đứng tên chồng có được chia khi ly hôn không?
U2: Nếu nhà đó được cha mẹ tặng riêng thì sao?
```

Resolved query:

```text
Nhà đứng tên chồng nhưng được cha mẹ tặng riêng có được chia khi ly hôn không?
```

Router decision:

```text
context_action=retrieve
retrievers:
  che_do_tai_san_cua_vo_chong
  chia_tai_san_sau_ly_hon
```

Lý do: “tặng riêng” mở thêm vấn đề phân loại tài sản. Context cũ không được dùng
để bỏ qua retriever.

### 5. Cache vô hiệu do ngày

Cache:

```text
target_date=2026-06-11
is_user_provided_date=false
```

Follow-up:

```text
Nếu sự việc xảy ra năm 2020 thì sao?
```

Router:

```text
time_scope=explicit
target_date=2020
```

Validator chuẩn hóa thành `2020-01-01`, phát hiện khác date/scope và fallback
sang retrieve.

### 6. Cache vô hiệu do KG version

Cache:

```text
kg_version=2026-06-11.1
```

Deployment mới:

```text
KG_VERSION=2026-06-12.1
```

Validator từ chối cache trước khi retriever chạy. Nếu không cấu hình
`KG_VERSION`, hệ thống dùng process-unique version nên cache cũng không sống qua
restart.

### 7. Kết hợp cache cũ và context mới

Follow-up cần hai retriever:

```text
chung_song_nhu_vo_chong → reuse ctx-cohabitation
cap_duong → retrieve mới
```

Context refs dùng:

```text
ctx-cohabitation
ctx-cap-duong-new
```

Hai encoded bundle được đưa qua Plan 1:

```text
decode → merge provision → role promotion → render
```

Điều khoản trùng giữa hai retriever chỉ xuất hiện một lần.

### 8. Resume thread

Persisted Router metadata:

```text
retrieval_memory_entries
turn_anchor
kg_version
```

`on_chat_resume` phục hồi:

```text
session_history
retrieval_memory
conversation_anchors
```

Sau resume, Router nhận lại descriptor của cache nhưng không nhận toàn bộ nội
dung pháp luật trong working history.

### 9. Hội thoại dài và token budget

Mặc định:

```text
RECENT_FULL_TURNS=4
ROUTER_HISTORY_MAX_TOKENS=3000
RESPONSE_HISTORY_MAX_TOKENS=4000
OLDER_TURN_INDEX_LIMIT=20
```

Working history:

```text
anchor cũ được xếp theo độ liên quan + độ gần
4 lượt gần nhất đầy đủ nếu còn budget
```

Token được ước lượng cục bộ, không gọi API. Phần mô tả retrieval memory cũng chỉ
gồm refs được anchor chọn và các entry gần nhất trong giới hạn.

### 10. Anchor mơ hồ dẫn đến clarify

Lịch sử cũ:

```text
turn-1: căn nhà mua trước hôn nhân
turn-5: mảnh đất được cha mẹ tặng riêng
```

Follow-up:

```text
Nếu tôi bán nó thì sao?
```

Router không được tự chọn một tài sản. Quyết định:

```json
{
  "tool": "clarify",
  "question": "Bạn đang hỏi về căn nhà mua trước hôn nhân hay mảnh đất được tặng riêng?"
}
```

Retriever calls: `0`.

Response LLM calls: `0`.

Final response path: Router → `clarify_question` → Chainlit direct message.

### 11. Thread legacy

Thread chỉ có `user_message` và `assistant_message`, không có metadata mới:

```text
retrieval_memory={}
anchors=[]
```

Router vẫn dùng các lượt gần nhất. Vì không có `context_ref`, mọi căn cứ cần
thiết được retrieve lại.

## Quan sát hệ thống

Trong Router step metadata:

- `router_policy`: candidate, resolved-query policy và retriever cuối.
- `tool_response[*].cache_status`: `retrieved` hoặc `reused`.
- `tool_response[*].cache_fallback_reason`: lý do reuse bị từ chối.
- `retrieval_memory_entries`: cache mới của lượt hiện tại.
- `turn_anchor`: chỉ mục compact dùng cho lượt sau.
- `kg_version`: phiên bản KG lúc xử lý.

Trong UI:

- `Retriever: <name>` nghĩa là retriever thực sự chạy.
- `Retriever cache: <name>` nghĩa là context được reuse.
- Không có step `Tổng hợp đáp án` khi Router dùng `clarify` hoặc `respond`.

Unit test liên quan:

```text
tests/test_conversation_context.py
tests/test_router_conversation.py
```
