# Tài liệu giao tiếp giữa các thành phần

Tài liệu mô tả cách các thành phần trong **Agentic GraphRAG Chatbot Luật** trao đổi dữ liệu với nhau. Hệ thống dùng **Chainlit** làm giao diện chat; logic nghiệp vụ (router, retriever, tổng hợp câu trả lời) có thể chạy **độc lập UI** qua các hàm Python nội bộ.

> **Lưu ý:** Đây không phải tài liệu REST API/OpenAPI. Chainlit giao tiếp với trình duyệt qua WebSocket; các thành phần backend giao tiếp qua **hàm async Python** và **giao thức OpenAI-compatible** (tool calling, chat completion).

---

## 1. Tổng quan kiến trúc

```text
┌──────────────────────────────────────────────────────────────────────────┐
│                         TRÌNH DUYỆT (Chainlit UI)                        │
│                    WebSocket + HTTP  →  localhost:8000                   │
└─────────────────────────────────┬────────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  presentation/main.py                                                    │
│  • Chainlit hooks (@cl.on_message, @cl.on_chat_start, @cl.on_chat_resume)│
│  • Registry tools (17 retriever + text2cypher + respond)                 │
│  • main_prompt → Response LLM stream                                     │
└───────┬──────────────────┬─────────────────────┬───────────────────────┘
        │                  │                     │
        ▼                  ▼                     ▼
 application/         adapter/retrievers/*    adapter/config.py
 router.py            (domain retriever)      • Neo4j driver (Bolt)
 query_updater.py     utils/utils.py          • LLM (Vercel AI Gateway)
 (tắt mặc định)       utils/general.py        • DATABASE_URL
                      (text2cypher)
        │                  │                     │
        ▼                  ▼                     ▼
 Vercel AI Gateway    Neo4j (Aura/local)    PostgreSQL
 (Router/Retriever/   Cypher queries        Chainlit Data Layer
  Response LLM)                             (threads, steps)
```

### Luồng xử lý một câu hỏi

```mermaid
sequenceDiagram
    participant U as Người dùng
    participant CL as Chainlit (main.py)
    participant R as Router (router.py)
    participant LLM_R as Router LLM
    participant T as Retriever(s)
    participant LLM_T as Retriever LLM
    participant N4J as Neo4j
    participant LLM_A as Response LLM
    participant PG as PostgreSQL

    U->>CL: Gửi tin nhắn (cl.Message)
    CL->>CL: Đọc session_history
    Note over CL: Query Updater hiện bị tắt
    CL->>R: route_question(question, tools, session_history)
    R->>LLM_R: bind_tools + ainvoke (tool calling)
    LLM_R-->>R: tool_calls[] (1..n tool)
    par Chạy song song
        R->>T: retriever(query)
        T->>LLM_T: structured output (TrichXuatLuat)
        LLM_T-->>T: dieu_luat_ids + thoi_diem_su_kien
        T->>N4J: execute_query(Cypher)
        N4J-->>T: Context_Tho records
        T-->>R: { raw_ids, contexts }
    end
    R-->>CL: list[RetrieverResult]
    CL->>LLM_A: chat_stream(main_prompt + contexts + history)
    LLM_A-->>CL: token stream
    CL->>U: Streaming câu trả lời
    CL->>CL: Cập nhật session_history
    CL->>PG: Lưu thread/steps (tự động qua Data Layer)
```

---

## 2. Chainlit hooks — giao diện người dùng

File: `presentation/main.py`

Chainlit là **entry point** duy nhất khi người dùng tương tác qua UI. Không có endpoint REST `/api/chat` trong production.

| Hook | Kích hoạt khi | Input | Output / Side effect |
|------|---------------|-------|----------------------|
| `@cl.oauth_callback` | Đăng nhập OAuth (Google/GitHub) thành công | `provider_id`, `token`, `raw_user_data`, `default_user` | `cl.User(identifier, metadata)` — lưu user vào PostgreSQL |
| `@cl.on_chat_start` | Bắt đầu cuộc hội thoại mới | — | Reset `session_history = []`; gửi tin chào mừng |
| `@cl.on_chat_resume` | User mở lại thread cũ từ sidebar | `thread: ThreadDict` (có `steps[]`) | Khôi phục `session_history` từ các step `user_message` / `assistant_message` |
| `@cl.on_message` | User gửi tin nhắn | `message: cl.Message` (`message.content`) | Router → Retriever → Response LLM stream; cập nhật `session_history` |

### Session state

| Key | Kiểu | Mô tả |
|-----|------|-------|
| `session_history` | `list[dict]` | Lịch sử hội thoại dạng OpenAI messages: `{ "role": "user"\|"assistant", "content": str }` |
| `user` | `cl.User` | Thông tin user (OAuth), dùng khi resume thread |

### Chainlit Steps (hiển thị trên UI)

Trong `@cl.on_message`, hệ thống tạo các step lồng nhau:

| Step name | Type | Input | Output |
|-----------|------|-------|--------|
| `Luồng truy xuất ngữ cảnh` | — | — | Tổng hợp bước truy xuất |
| `Router Agent` | `tool` | Câu hỏi đã cập nhật | Metadata `tool_response` |
| `Retriever: {tool_name}` | — | `query` | Context text hoặc raw result |
| `Tổng hợp đáp án` | `llm` | Context gửi LLM | Câu trả lời đầy đủ (stream) |

---

## 3. Router contract

File: `application/router.py`

### Hàm chính

```python
async def route_question(
    question: str,
    tools: dict[str, any],
    answers: list[dict[str, str]],  # session_history
) -> list[RetrieverResult | str | list]
```

| Tham số | Kiểu | Mô tả |
|---------|------|-------|
| `question` | `str` | Câu hỏi đã làm rõ (hiện tại = nguyên văn input, vì Query Updater tắt) |
| `tools` | `dict` | Registry từ `presentation/main.py`: `{ name: { description, function } }` |
| `answers` | `list[dict]` | Lịch sử hội thoại, truyền vào prompt router |

**Return:** Danh sách kết quả từ từng retriever được gọi **song song** (`asyncio.gather`). Mỗi phần tử thường là `RetrieverResult` (dict có `contexts`).

### Luồng nội bộ

```text
route_question
    │
    ├─► tool_choice(messages, tools=[...descriptions])
    │       LLM: ROUTER_LLM (bind_tools, tool_choice="any")
    │       Return: res.tool_calls  →  [{ "name": str, "args": dict }, ...]
    │
    └─► handle_tool_calls(tools, llm_tool_calls, question)
            • Loại trùng tool (mỗi tool chỉ gọi 1 lần)
            • asyncio.gather → _execute_tool_call cho từng tool
            • Mỗi call: tools[name]["function"](query=question)
```

### Router LLM — message format

```python
[
    {"role": "system", "content": tool_picker_prompt},
    *session_history,   # optional context
    {"role": "user", "content": "Câu hỏi của người dùng cần tìm công cụ để giải quyết: '{question}'"},
]
```

Tools truyền vào LLM là danh sách schema OpenAI function: `[tool["description"] for tool in tools.values()]`.

---

## 4. Tool schema — Tool Catalog

Mỗi retriever đăng ký trong `presentation/main.py` (`tools` dict) gồm:

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `description` | `dict` | OpenAI function schema (`type: "function"`) |
| `function` | `async callable` | Hàm thực thi retriever |

### Schema chuẩn (domain retriever)

Hầu hết retriever domain dùng cùng parameter:

```json
{
  "type": "function",
  "function": {
    "name": "<tool_name>",
    "description": "<mô tả chủ đề pháp luật>",
    "parameters": {
      "type": "object",
      "properties": {
        "query": {
          "type": "string",
          "description": "Câu hỏi cụ thể của người dùng"
        }
      },
      "required": ["query"]
    }
  }
}
```

### Danh sách tool (17 + 2 utility)

| Tool name | Module | Chủ đề |
|-----------|--------|--------|
| `quy_dinh_chung_khai_niem_phap_ly` | `adapter/retrievers/quy_dinh_chung_khai_niem_phap_ly.py` | Quy định chung, khái niệm pháp lý |
| `dieu_kien_ket_hon` | `adapter/retrievers/ket_hon/dieu_kien_ket_hon.py` | Điều kiện kết hôn |
| `dang_ky_ket_hon` | `adapter/retrievers/ket_hon/dang_ky_ket_hon.py` | Đăng ký kết hôn |
| `ket_hon_trai_phap_luat` | `adapter/retrievers/ket_hon/ket_hon_trai_phap_luat.py` | Kết hôn trái pháp luật |
| `chung_song_nhu_vo_chong` | `adapter/retrievers/ket_hon/chung_song_nhu_vo_chong.py` | Chung sống như vợ chồng |
| `hon_nhan_cham_dut_do_vo_chong_chet` | `adapter/retrievers/hon_nhan_cham_dut_do_vo_chong_chet.py` | Hôn nhân chấm dứt do vợ/chồng chết |
| `cap_duong` | `adapter/retrievers/cap_duong.py` | Nghĩa vụ cấp dưỡng |
| `quan_he_hon_nhan_co_yeu_to_nuoc_ngoai` | `adapter/retrievers/quan_he_hon_nhan_co_yeu_to_nuoc_ngoai.py` | Hôn nhân có yếu tố nước ngoài |
| `tai_san_rieng_cua_con` | `adapter/retrievers/tai_san_rieng_cua_con.py` | Tài sản riêng của con |
| `quy_dinh_chung_ly_hon` | `adapter/retrievers/ly_hon/quy_dinh_chung_ly_hon.py` | Quy định chung ly hôn |
| `chia_tai_san_sau_ly_hon` | `adapter/retrievers/ly_hon/chia_tai_san_sau_ly_hon.py` | Chia tài sản sau ly hôn |
| `cha_me_con_sau_ly_hon` | `adapter/retrievers/ly_hon/cha_me_con_sau_ly_hon.py` | Cha mẹ, con sau ly hôn |
| `quyen_nghia_vu_vo_chong` | `adapter/retrievers/quan_he_giua_vo_va_chong/quyen_nghia_vu_vo_chong.py` | Quyền, nghĩa vụ vợ chồng |
| `dai_dien_trach_nhiem_vo_chong` | `adapter/retrievers/quan_he_giua_vo_va_chong/dai_dien_trach_nhiem_vo_chong.py` | Đại diện, trách nhiệm vợ chồng |
| `che_do_tai_san_cua_vo_chong` | `adapter/retrievers/quan_he_giua_vo_va_chong/che_do_tai_san_cua_vo_chong.py` | Chế độ tài sản vợ chồng |
| `xu_phat_vi_pham` | `adapter/retrievers/vi_pham/xu_phat_vi_pham.py` | Xử phạt vi phạm hành chính |
| `text2cypher` | `utils/general.py` | Truy vấn đồ thị tổng quát (fallback) |
| `respond` | `utils/general.py` | Trả lời không cần truy xuất / trò chuyện phiếm |

### Tool đặc biệt

**`text2cypher`** — parameter `query: str`; return `list[dict]` (raw Neo4j records) hoặc chuỗi lỗi, **không** qua `chuan_hoa_ket_qua_retriever`.

**`respond`** — parameter `answer: str`; return chuỗi trả lời trực tiếp, không truy Neo4j.

---

## 5. Retriever contract

### Input

```python
async def <tool_name>(query: str) -> RetrieverResult | list | str
```

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `query` | `str` | Câu hỏi người dùng (router truyền nguyên văn `updated_question`) |

### Bước xử lý nội bộ (domain retriever)

```text
1. Retriever LLM (structured output)
       Input:  prompt_extract + query
       Schema: TrichXuatLuat (Pydantic)
       Output: dieu_luat_ids[], thoi_diem_su_kien

2. Chuẩn hóa thời gian
       lay_target_date_tu_extraction() → (target_date, is_user_provide_date)

3. Neo4j Cypher
       driver.execute_query(cypher, danh_sach_id=..., target_date=...)

4. Chuẩn hóa kết quả
       chuan_hoa_ket_qua_retriever(records, target_date, is_user_provide_date)
```

### Structured output — `TrichXuatLuat`

File: `utils/utils.py`

```python
class TrichXuatLuat(BaseModel):
    dieu_luat_ids: List[str]      # VD: ["Luat_HNGD_2014_Dieu_107", ...]
    thoi_diem_su_kien: Optional[str]  # YYYY-MM-DD hoặc null
```

### Output chuẩn — `RetrieverResult`

File: `utils/utils.py` — `chuan_hoa_ket_qua_retriever()`

```python
{
    "raw_ids": {
        "can_cu_chinh": ["Luat_HNGD_2014_Dieu_107", ...],
        "can_cu_huong_dan": [...],
        "can_cu_bo_tro": [...]
    },
    "contexts": [
        "<string đã format cho LLM — THÔNG TIN CẢNH BÁO, HIỆU LỰC, CĂN CỨ CHÍNH, ...>"
    ]
}
```

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `raw_ids` | `dict[str, list[str]]` | ID điều luật thô, dùng cho benchmark/metric |
| `contexts` | `list[str]` | Text context đã chuẩn hóa, gộp vào prompt Response LLM |

Mỗi phần tử trong `contexts` chứa các section:

- `--- THÔNG TIN CẢNH BÁO ---` (lịch sử, ưu tiên cấp bậc, sửa đổi)
- `--- THÔNG TIN HIỆU LỰC VĂN BẢN ---`
- `--- CĂN CỨ CHÍNH ---`
- `--- CĂN CỨ THAM CHIẾU BỔ TRỢ ---` (nếu có)
- `--- CĂN CỨ HƯỚNG DẪN ---` (nếu có)
- `--- VĂN BẢN THAY THẾ ---` (nếu có)

### Gộp context cho Response LLM

File: `presentation/main.py`

```python
contexts_for_llm = []
for res in tool_response:
    if isinstance(res, dict) and "contexts" in res:
        contexts_for_llm.extend(res["contexts"])
    else:
        contexts_for_llm.append(res)

contexts_text_for_llm = "\n\n".join(str(ctx) for ctx in contexts_for_llm)
```

---

## 6. Response LLM contract

File: `adapter/config.py`, gọi từ `presentation/main.py`

### Hàm stream

```python
async def chat_stream(messages, **config) -> AsyncIterator[str]
```

### Message format

```python
[
    {"role": "system", "content": main_prompt},
    *session_history,
    {"role": "system", "content": f"Dữ liệu lấy được từ hệ thống cho câu hỏi '{updated_question}':\n{contexts_text_for_llm}"},
    {"role": "user", "content": f"Câu hỏi của người dùng: {input_text}"},
]
```

| Thành phần | Model env | Mặc định | max_tokens |
|------------|-----------|----------|------------|
| Router | `ROUTER_LLM` | `openai/gpt-4o` | 2048 |
| Retriever | `RETRIEVER_LLM` | `openai/o3` | 1024 |
| Response | `RESPONSE_LLM` | `openai/gpt-4.1` | 4096 |

---

## 7. Query Updater (tùy chọn, hiện tắt)

File: `application/query_updater.py`

```python
async def query_update(input: str, answers: list) -> str
```

| Input | Output |
|-------|--------|
| Câu hỏi gốc + `session_history` | Câu hỏi đã bổ sung ngữ cảnh (JSON `{"question": "..."}`) |

Trong `presentation/main.py`, bước này **đang comment** — `updated_question = input_text`.

---

## 8. Neo4j — giao tiếp đồ thị pháp luật

File: `adapter/config.py`

### Kết nối

| Biến môi trường | Mô tả |
|-----------------|-------|
| `NEO4J_URI` | Bolt URI, VD: `bolt://localhost:7687` hoặc `neo4j+ssc://*.databases.neo4j.io` (Aura) |
| `NEO4J_USERNAME` | Username |
| `NEO4J_PASSWORD` | Password |
| `NEO4J_DATABASE` | Tên database |

```python
driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
records, _, _ = driver.execute_query(cypher, **params)
```

### Node label chính

| Label | Vai trò | Thuộc tính quan trọng |
|-------|---------|------------------------|
| `DieuLuat` | Điều/Khoản/Điểm luật | `id`, `noidung`, `cap_bac_phap_ly`, `ngay_co_hieu_luc`, `ngay_het_hieu_luc` |

ID node theo convention: `{TenVanBan}_Dieu_{so}` — VD: `Luat_HNGD_2014_Dieu_107`.

### Quan hệ (relationships)

| Quan hệ | Ý nghĩa |
|---------|---------|
| `CO_KHOAN`, `CO_DIEM` | Cấu trúc phân cấp Điều → Khoản → Điểm |
| `THAY_THE_BOI` | Phiên bản theo thời gian (luật cũ ↔ mới) |
| `DUOC_SUA_DOI_BOI` | Văn bản sửa đổi, bổ sung |
| `HUONG_DAN_BOI` | Nghị định/Thông tư hướng dẫn |
| `THAM_CHIEU_DEN` | Tham chiếu chéo giữa điều luật |

### Cypher pattern (domain retriever)

Tất cả retriever domain dùng cùng khung truy vấn:

```cypher
MATCH (n_goc:DieuLuat) WHERE n_goc.id IN $danh_sach_id

OPTIONAL MATCH (n_goc)-[:CO_KHOAN|CO_DIEM*0..2]->(chi_tiet_goc)
OPTIONAL MATCH (chi_tiet_goc)-[:THAY_THE_BOI*0..]-(chi_tiet_gia_toc)

// Lọc phiên bản có hiệu lực tại $target_date
WITH DISTINCT n_goc, node_xet_duyet AS chi_tiet_ap_dung
WHERE chi_tiet_ap_dung.ngay_co_hieu_luc <= $target_date
  AND (chi_tiet_ap_dung.ngay_het_hieu_luc IS NULL
       OR chi_tiet_ap_dung.ngay_het_hieu_luc > $target_date)

OPTIONAL MATCH (chi_tiet_ap_dung)-[:DUOC_SUA_DOI_BOI]->(van_ban_sua_doi)
OPTIONAL MATCH (chi_tiet_ap_dung)-[:HUONG_DAN_BOI]->(huong_dan)
OPTIONAL MATCH (chi_tiet_ap_dung)-[:THAY_THE_BOI*1..]->(hien_hanh)
OPTIONAL MATCH (chi_tiet_ap_dung)-[:THAM_CHIEU_DEN]->(luat_tham_chieu)

RETURN { ... } AS Context_Tho
```

### Tham số Cypher

| Param | Kiểu | Nguồn |
|-------|------|-------|
| `$danh_sach_id` | `list[str]` | `TrichXuatLuat.dieu_luat_ids` |
| `$target_date` | `str` (YYYY-MM-DD) | `lay_target_date_tu_extraction()` hoặc ngày hiện tại |

### Return object `Context_Tho`

| Key | Mô tả |
|-----|-------|
| `can_cu_chinh` | Căn cứ chính (Điều/Khoản/Điểm áp dụng) |
| `can_cu_huong_dan` | Văn bản hướng dẫn |
| `can_cu_bo_tro` | Tham chiếu bổ trợ |
| `quy_dinh_hien_hanh_doi_chieu` | ID văn bản thay thế (đối chiếu luật cũ) |

### text2cypher (fallback)

File: `utils/general.py` + `adapter/text2cypher.py`

LLM sinh Cypher tự do từ câu hỏi → `driver.execute_query(cypher)` → trả raw records, không qua pipeline chuẩn hóa context.

---

## 9. LLM Gateway — Vercel AI Gateway

File: `adapter/config.py`

### Endpoint

| Biến | Giá trị mặc định |
|------|------------------|
| `AI_GATEWAY_BASE_URL` | `https://ai-gateway.vercel.sh/v1` |
| `VERCEL_AI_GATEWAY_API_KEY` | Bắt buộc |

Giao thức: **OpenAI-compatible** (`langchain_openai.ChatOpenAI`).

### Ba vai trò LLM

```text
┌─────────────────┐     bind_tools      ┌──────────────┐
│   Router LLM    │ ──────────────────► │  tool_calls  │
│  (ROUTER_LLM)   │                     └──────────────┘
└─────────────────┘

┌─────────────────┐  with_structured_output  ┌────────────────┐
│ Retriever LLM   │ ────────────────────────► │ TrichXuatLuat  │
│ (RETRIEVER_LLM) │                           └────────────────┘
└─────────────────┘

┌─────────────────┐      astream           ┌────────────────┐
│ Response LLM    │ ──────────────────────► │ token stream   │
│ (RESPONSE_LLM)  │                         └────────────────┘
└─────────────────┘
```

### Builder functions

| Hàm | Model | Temperature |
|-----|-------|-------------|
| `build_router_llm()` | `ROUTER_LLM` | 0 |
| `build_retriever_llm()` | `RETRIEVER_LLM` | 0 |
| `build_response_llm()` | `RESPONSE_LLM` | 0 |
| `chat()` / `chat_stream()` | `RESPONSE_LLM` | 0 |

---

## 10. PostgreSQL — Chainlit Data Layer

File: `adapter/data_layer.py`

### Kết nối

```ini
DATABASE_URL=postgresql+asyncpg://postgres:123456@localhost:5432/chainlit_db
```

```python
data_layer = SQLAlchemyDataLayer(conninfo=DATABASE_URL)
cl_data._data_layer = data_layer
```

Nếu thiếu `DATABASE_URL`: chat vẫn chạy, **không** persist thread.

### Schema (Chainlit)

File tham khảo: `adapter/init_db.py`

| Bảng | Mục đích |
|------|----------|
| `users` | User OAuth (`identifier`, `metadata`) |
| `threads` | Cuộc hội thoại (`name`, `userId`, `tags`, `metadata`) |
| `steps` | Từng bước trong thread (`type`, `input`, `output`, `metadata`, `parentId`) |
| `elements` | File/element đính kèm |
| `feedbacks` | Phản hồi người dùng |

### Step types liên quan chat

| `type` | Nguồn | Dùng khi resume |
|--------|-------|-----------------|
| `user_message` | Tin nhắn người dùng | Khôi phục `role: user` |
| `assistant_message` | Câu trả lời bot | Khôi phục `role: assistant` |
| `tool` | Router / Retriever steps | Hiển thị UI, không đưa vào `session_history` |
| `llm` | Bước tổng hợp đáp án | Hiển thị UI |

Chainlit tự tạo schema khi khởi động lần đầu với `DATABASE_URL` hợp lệ.

---

## 11. Luồng benchmark — programmatic interface

File: `benchmark_dataset/scripts/fill_test_answers.py`

Script benchmark **bypass Chainlit UI**, gọi trực tiếp cùng logic nghiệp vụ:

```text
fill_test_answers.py
    │
    ├─ import tools, main_prompt từ presentation/main.py
    ├─ import tool_choice, tool_picker_prompt từ application/router.py
    └─ import chat_stream từ adapter/config.py
```

### Pipeline mỗi câu hỏi benchmark

```python
# 1. Truy xuất context (không qua @cl.on_message)
tool_response = await retrieve_context(question)
#    → tool_choice() → execute_tool_call() song song

# 2. Sinh câu trả lời
answer = await generate_answer(question, tool_response)
#    → chat_stream(main_prompt + contexts)

# 3. Ghi vào JSON test
row["context"] = json.dumps(tool_response)      # raw retriever output
row["chatbot_answer"] = answer
```

### So sánh Chainlit UI vs Benchmark

| Khía cạnh | Chainlit UI | Benchmark script |
|-----------|-------------|------------------|
| Entry point | `@cl.on_message` | `retrieve_context()` + `generate_answer()` |
| Router | `route_question()` (có `cl.Step`) | `tool_choice()` + `execute_tool_call()` (không Step) |
| Session history | Có — truyền vào router | Không — mỗi câu độc lập |
| Query Updater | Tắt (`updated_question = input`) | Không dùng |
| Response LLM | `chat_stream()` + UI stream | `chat_stream()` — gom token |
| Persist | PostgreSQL (thread/steps) | Ghi file JSON |
| Context lưu trữ | Trong step metadata | `row["context"]` = JSON raw `tool_response` |

### Lệnh chạy

```bash
python -m benchmark_dataset.scripts.fill_test_answers benchmark_dataset/test_versions/cap_duong/test_v1_1705_cap_duong.json
```

---

## 12. Sơ đồ hợp đồng dữ liệu tổng hợp

```text
User Input (str)
    │
    ▼
session_history: list[{ role, content }]
    │
    ▼
Router LLM ──► tool_calls: [{ name, args }]
    │
    ▼ (parallel, per tool)
Retriever(query: str)
    │
    ├─► TrichXuatLuat { dieu_luat_ids, thoi_diem_su_kien }
    ├─► Neo4j → Context_Tho
    └─► RetrieverResult { raw_ids, contexts[] }
    │
    ▼
contexts_text: str  (join contexts)
    │
    ▼
Response LLM (stream) ──► Answer (str)
    │
    ▼
session_history += [user, assistant]
    │
    ▼
PostgreSQL (threads, steps)  ← Chainlit Data Layer
```

---

## 13. File tham chiếu

| File | Vai trò trong giao tiếp |
|------|------------------------|
| `presentation/main.py` | Chainlit hooks, tool registry, orchestration |
| `application/router.py` | Router LLM + parallel tool execution |
| `application/query_updater.py` | Làm rõ câu hỏi theo lịch sử (tắt) |
| `adapter/config.py` | Neo4j driver, LLM builders, `chat_stream` |
| `adapter/data_layer.py` | Chainlit ↔ PostgreSQL |
| `adapter/retrievers/*` | Domain retriever + Cypher |
| `utils/utils.py` | `TrichXuatLuat`, `chuan_hoa_ket_qua_retriever` |
| `utils/general.py` | `text2cypher`, `respond` |
| `benchmark_dataset/scripts/fill_test_answers.py` | Programmatic interface (benchmark) |
| `deploy.md` | Triển khai Docker, môi trường, truy cập |

---

## 14. Ghi chú mở rộng

- **Thêm retriever mới:** Tạo module trong `adapter/retrievers/`, khai báo `{name}_description` + hàm async, đăng ký vào `tools` trong `presentation/main.py`.
- **REST API cho bên thứ ba:** Hiện chưa có. Cần tách logic từ `route_question` + `chat_stream` ra service layer và bọc FastAPI nếu muốn expose HTTP.
- **Chainlit WebSocket:** Không document chi tiết ở đây — protocol nội bộ phục vụ UI, không phải integration point cho hệ thống khác.
