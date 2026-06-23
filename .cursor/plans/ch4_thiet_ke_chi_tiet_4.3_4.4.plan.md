---
name: §4.3 + §4.4 — Thiết kế chi tiết gói + Luồng Agentic Workflow (viết lại)
overview: |
  Viết mới §4.3 "Thiết kế chi tiết gói" theo hướng module/feature-group thay vì class
  diagram OOP (codebase Python procedural). Viết LẠI HOÀN TOÀN §4.4 "Thiết kế chi tiết
  luồng Agentic Workflow" (7 sub-subsection) vì §4.4 hiện tại có nhiều sai lệch so với
  code. XÓA HOÀN TOÀN mục "Thiết kế lớp" (dòng 168–265 file 4_Ket_qua_thuc_nghiem.tex).
  §4.4 mới (đã ở vị trí hiện tại trong section "Thiết kế kiến trúc") thay thế chức năng
  của "Thiết kế lớp" cũ.
todos:
  - id: 4.3-frame
    content: §4.3 — Đoạn mở đầu + bảng ánh xạ "UML OOP → Module Python" (giải thích vì sao không dùng class diagram)
    status: pending
  - id: 4.3.2-router-retriever
    content: §4.3.2 — Pipeline điều phối Router – Retriever (module diagram + bảng + lstinputlisting RetrieverSpec dataclass)
    status: pending
  - id: 4.3.3-memory-reuse
    content: §4.3.3 — Bộ nhớ hội thoại và cache reuse (module diagram + bảng + lstinputlisting ReuseValidation)
    status: pending
  - id: 4.3.4-bundle-dedupe
    content: §4.3.4 — Bundle căn cứ pháp lý và dedupe context (data-flow diagram + bảng khóa dedupe)
    status: pending
  - id: 4.3.5-retriever-template
    content: §4.3.5 — Truy xuất theo template Cypher (retriever đại diện che_do_tai_san_cua_vo_chong)
    status: pending
  - id: 4.3.6-guest-data-layer
    content: §4.3.6 — Quản lý phiên & quyền guest (UML có inheritance GuestAwareSQLAlchemyDataLayer ← SQLAlchemyDataLayer)
    status: pending
  - id: 4.3.7-viz-pipeline
    content: §4.3.7 — Pipeline trực quan đồ thị tri thức (lazy → materialize → cache)
    status: pending
  - id: delete-thiet-ke-lop
    content: XÓA dòng 168–265 ("Thiết kế lớp" + module main + module router + sequence diagram tư vấn pháp lý + comment use case khôi phục)
    status: pending
  - id: 4.4.1-end-to-end
    content: §4.4.1 — Sơ đồ end-to-end (swimlane 4 lane) + bảng 7 pha
    status: pending
  - id: 4.4.2-router
    content: §4.4.2 — Đặc tả Router Agent + bảng phụ 5 field control + lstinputlisting tool_picker_prompt (excerpt)
    status: pending
  - id: 4.4.3-retriever
    content: §4.4.3 — Đặc tả Retriever Agent (3 pha CLASSIFY/EXTRACT/EXECUTE) + bảng 20 retriever × số template
    status: pending
  - id: 4.4.4-direct-tools
    content: §4.4.4 — Đặc tả Direct Tools (clarify/respond/text2cypher) + cơ chế exclusive
    status: pending
  - id: 4.4.5-response-llm
    content: §4.4.5 — Đặc tả Response LLM (Tổng hợp đáp án)
    status: pending
  - id: 4.4.6-cache-reuse
    content: §4.4.6 — Cơ chế cache reuse + bảng 5 luật + sequence diagram nhỏ
    status: pending
  - id: 4.4.7-resume
    content: §4.4.7 — Khôi phục phiên hội thoại (resume thread)
    status: pending
  - id: drawio-4.3
    content: Tạo 6 file .drawio cho §4.3 trong Hinhve/Thiet_ke_chi_tiet_goi/
    status: pending
  - id: drawio-4.4
    content: Tạo 2 file .drawio cho §4.4 (swimlane end-to-end + sequence cache reuse)
    status: pending
  - id: export-png
    content: Sinh viên export .drawio → .png 200 DPI
    status: pending
  - id: build
    content: Chạy scripts/build-thesis.ps1 kiểm tra \ref{} resolve
    status: pending
isProject: false
---

# Plan §4.3 + §4.4 — Thiết kế chi tiết (viết lại)

## Tham chiếu

- File LaTeX: [`ĐATN_.../Chuong/4_Ket_qua_thuc_nghiem.tex`](ĐATN_20225919_Lê_Thái_Sơn_Chatbot_tư_vấn_luật_hôn_nhân_gia_đình/Chuong/4_Ket_qua_thuc_nghiem.tex)
  - §4.3 hiện tại: dòng 45–57 (chỉ là hướng dẫn template, không có nội dung thật)
  - §4.4 hiện tại: dòng 59–134 (Main Agent / Router Agent / Retriever Agent — SAI nhiều điểm)
  - "Thiết kế lớp" hiện tại: dòng 168–265 (sẽ XÓA HOÀN TOÀN)
- Code map: [`thesis-context/ch05-code-map.md`](thesis-context/ch05-code-map.md), [`thesis-context/chat-flow.md`](thesis-context/chat-flow.md), [`thesis-context/AGENT_WORKFLOW.md`](thesis-context/AGENT_WORKFLOW.md)
- Plan §4.2 đã hoàn thành: [`.cursor/plans/thiet_ke_tong_quan_4.2_2_pha.plan.md`](.cursor/plans/thiet_ke_tong_quan_4.2_2_pha.plan.md)

## Cấu trúc chương 4 sau khi sửa

| § | Trạng thái | Nội dung |
|---|---|---|
| 4.1 Lựa chọn kiến trúc phần mềm | giữ | client–server |
| 4.2.1/4.2.2 Thiết kế tổng quan | giữ | sơ đồ gói server + client (đã viết ở Pha 2 plan trước) |
| **4.3 Thiết kế chi tiết gói** | **viết mới** | 7 sub-subsection (đoạn mở đầu + 6 nhóm vấn đề) |
| **4.4 Thiết kế chi tiết luồng Agentic Workflow** | **viết lại hoàn toàn** | 7 sub-subsection |
| Thiết kế giao diện | giữ | login, main chat, agent trace |
| ~~Thiết kế lớp~~ | **XÓA** | dòng 168–265 |
| Thiết kế cơ sở dữ liệu | giữ | ER + 4 bảng Users/Threads/Steps/Feedbacks |

---

## §4.3 Thiết kế chi tiết gói

**Định hướng phương pháp**: codebase Python procedural không có class hierarchy đáng kể (chỉ một số `@dataclass(frozen=True)` value object + đúng một class inheritance thật `GuestAwareSQLAlchemyDataLayer ← SQLAlchemyDataLayer`). Vẽ class diagram OOP cho từng package theo template gốc sẽ ra diagram trống hoặc lặp §4.2. Thay vào đó:

- **Đơn vị thiết kế**: module + dataclass + hàm public (thay cho class + thuộc tính + phương thức).
- **Tổ chức**: theo "nhóm gói cùng giải quyết 1 vấn đề" (template gốc cho phép) thay vì 1 sub-subsection / package.
- **Quan hệ UML giữ lại**: dependency (import) — phổ biến; association (truyền dataclass) — phổ biến; aggregation/composition — chỉ ở chỗ thực sự có collection; inheritance — chỉ 1 lần duy nhất; implementation — ở các hook Chainlit/FastAPI.

### §4.3 Đoạn mở đầu + bảng ánh xạ UML → module Python

Bảng đầu chương:

| UML OOP gốc | Tương đương trong codebase Python |
|---|---|
| Lớp | Module Python (file `.py`) hoặc hàm public chính |
| Thuộc tính lớp | Hằng số module (`RETRIEVER_SPECS`, `tool_picker_prompt`, `RECENT_FULL_TURNS`…) |
| Phương thức | Hàm public của module |
| Phụ thuộc (dependency) | `import` / lời gọi hàm |
| Kết hợp (association) | Hàm truyền data structure giữa hai module |
| Kết tập / hợp thành | Catalog chứa list spec (`RETRIEVER_SPECS`); bundle chứa list provision (`LegalContextBundle`) |
| Kế thừa (inheritance) | **Chỉ 1 chỗ:** `GuestAwareSQLAlchemyDataLayer ← SQLAlchemyDataLayer` (§4.3.6) |
| Thực thi (implementation) | Decorator Chainlit/FastAPI: `@cl.on_chat_start`, `@cl.on_message`, `@cl.on_chat_resume`, `app.middleware("http")` |

### §4.3.2 Pipeline điều phối Router – Retriever

**Phạm vi**: `application/router.py`, `application/retriever_catalog.py` (`RetrieverSpec`, `TriggerRule`, `RETRIEVER_SPECS`), `application/router_tool_registry.py`, `application/retriever_tools.py`, `application/adapter_router_descriptions.py`, `adapter/retrievers/*` (gộp 1 hộp), `adapter/direct_tools.py`.

**Quan hệ vẽ**:
- Dependency: `router → retriever_catalog → retrievers/*`
- Aggregation (kim cương rỗng): `RETRIEVER_SPECS` chứa nhiều `RetrieverSpec`
- Association qua data: `tool_call (dict)` Router → retriever
- Direct tool đặt vào nhóm exclusive ở rìa

**Bảng kèm**: 4 cột (Module / Hàm public chính / Hằng số module / Trách nhiệm).

**lstinputlisting**: `RetrieverSpec` + `TriggerRule` dataclass (15–20 dòng).

**Ghi chú**: KHÔNG mô tả `retriever_policy` là filter bắt buộc (đang bị tắt trong production).

### §4.3.3 Bộ nhớ hội thoại và cache reuse retriever

**Phạm vi**: `application/conversation_context.py` (`ReuseValidation`, `build_working_history`, `validate_reuse_request`, `create_retrieval_memory_entries`, `build_turn_anchor`, `restore_conversation_state`, `current_kg_version`, `estimate_tokens`), `presentation/main.py` (session vars), `application/router.py::_reuse_tool_call`.

**Quan hệ vẽ**:
- Dependency: `main.py → conversation_context`, `router → conversation_context.validate_reuse_request`
- Aggregation: `retrieval_memory: list[RetrievalMemoryEntry]`
- Implementation: 3 hook Chainlit `@cl.on_chat_start/@cl.on_message/@cl.on_chat_resume`

**Bảng kèm**: 3 cấu trúc dữ liệu in-memory + 5 biến môi trường budget (`RECENT_FULL_TURNS`, `ROUTER_HISTORY_MAX_TOKENS`, `RESPONSE_HISTORY_MAX_TOKENS`, `OLDER_TURN_INDEX_LIMIT`, `KG_VERSION`).

**lstinputlisting**: `ReuseValidation` dataclass (~10 dòng).

### §4.3.4 Bundle căn cứ pháp lý và dedupe context (data-flow)

**Phạm vi**: `utils/legal_context_codec.py`, `application/legal_context.py` (`ContextPipelineResult`, `process_context_strings`, `merge_legal_context_bundles`, `render_legal_context_bundle`), `utils/utils.py::chuan_hoa_Context_cho_LLM`, `application/warning_payload.py`.

**Hình**: data-flow diagram (không phải module diagram):

```
Context_Tho (dict Neo4j) → encode_context_record → "LEGAL_CONTEXT_BUNDLE_V1:..."
list[str] → process_context_strings → group(target_date, is_user_provided_date)
→ merge_legal_context_bundles → render_legal_context_bundle
→ chuan_hoa_Context_cho_LLM → text gửi Response LLM
```

**Bảng kèm**:
- Khóa dedupe provision: `(id + amendment_id + effective_from + effective_until)`
- Thứ tự ưu tiên role: `main > guidance > support`

**Đoạn ghi chú**: trạng thái mixed-compatible — một số retriever còn trả legacy text (không bịa rằng đã migrate hết).

### §4.3.5 Truy xuất theo template Cypher (retriever đại diện)

**Retriever chọn (recommended)**: `che_do_tai_san_cua_vo_chong` — đã có map trong `ch05-code-map.md`, phức tạp đủ minh họa 2 pha expand+time filter.

**Phạm vi**: `adapter/retrievers/quan_he_giua_vo_va_chong/che_do_tai_san_cua_vo_chong.py`, `adapter/cypher_templates/tai_san/__init__.py` (`TemplateRegistry`, `CypherTemplate`), `adapter/cypher_templates/tai_san/_common.py` (`TOPIC_LABEL`, `EXPAND_AND_TIMEFILTER_CYPHER`), `adapter/cypher_templates/tai_san/term_mapping.py`, `adapter/retrievers/_context_tho_common.py`, `adapter/config.py` (`driver`, LLM client).

**Quan hệ vẽ**:
- Dependency: retriever → registry → template → `_common`
- Aggregation: `TemplateRegistry` chứa nhiều `CypherTemplate` (pattern lặp ở 20 domain)
- Association qua data: `runtime_params (dict)` → `EXPAND_AND_TIMEFILTER_CYPHER` → `Context_Tho`

**Bảng kèm**: 3 cột (Pha / Module / Output).

**Đoạn diễn giải**: nhấn mạnh thiết kế tách `_common.py` cho `EXPAND_AND_TIMEFILTER` (giải quyết hiệu lực thời gian) — chương 5 sẽ đi sâu, ở đây chỉ kiến trúc.

### §4.3.6 Quản lý phiên & quyền guest (UML có inheritance)

**Phạm vi**: `adapter/data_layer.py` (`GuestAwareSQLAlchemyDataLayer`), `adapter/guest.py` (`is_guest_identifier`, `is_guest_user`, `is_guest_context`, `create_persisted_guest`), `presentation/guest_auth.py` (`guest_router`, `guest_management_guard`, `is_guest_management_request`), `presentation/projects_api.py`, `adapter/projects.py`.

**Đây là chỗ DUY NHẤT có inheritance thật**:
- `SQLAlchemyDataLayer` (Chainlit base) ← `GuestAwareSQLAlchemyDataLayer`
- Liệt kê 11 method override: `get_user`, `create_user`, `update_thread`, `delete_thread`, `create_step`, `update_step`, `delete_step`, `create_element`, `delete_element`, `upsert_feedback`, `delete_feedback`

**Quan hệ vẽ**:
- Inheritance (mũi tên tam giác rỗng): duy nhất chỗ này
- Dependency: `data_layer → guest`, `projects_api → guest`, `projects_api → projects`
- Implementation: `guest_management_guard` cài qua `app.middleware("http")`

**Bảng kèm**: ma trận quyền (Thao tác × Guest/User) trích từ `data_layer.py`.

**lstinputlisting**: `GuestAwareSQLAlchemyDataLayer` (~30 dòng — toàn bộ class, file ngắn).

### §4.3.7 Pipeline trực quan đồ thị tri thức

**Phạm vi**: `adapter/graph_viz.py` (`_GraphBuilder`, `build_graph_payload`, `merge_graph_payloads`, `save_lazy_viz_stub`, `materialize_viz_payload`, `resolve_viz_snapshot`, `collect_viz_links`, `params_for_display`), `adapter/viz_store.py`, `presentation/viz_routes.py`, static `viz/`.

**Quan hệ vẽ**:
- Composition (kim cương đặc): `_GraphBuilder` chứa list `Node` và list `Edge`
- Dependency: `viz_routes → viz_store → file system snapshot`, `viz_routes → graph_viz`, retriever → `save_lazy_viz_stub`
- Association: `tool_response` → `collect_viz_links` → URL embed câu trả lời

**Bảng kèm**: 3 cột (Pha lazy → materialize → cache / Module / Trigger).

**lstinputlisting**: chữ ký `save_lazy_viz_stub` + `materialize_viz_payload` (~10–15 dòng).

---

## §4.4 Thiết kế chi tiết luồng Agentic Workflow (viết lại hoàn toàn)

### Các điểm sai cần loại bỏ khỏi §4.4 cũ

| Điểm sai trong §4.4 cũ | Thực tế trong codebase |
|---|---|
| "Main Agent" làm tâm điều phối | Không tồn tại — flow chính là `on_message` hook + Response LLM stream |
| 5 bước | Thực tế 7 pha (thêm working_history, retrieval memory, dedupe bundle, legal warning) |
| Router không có 5 field control | Code có `confidence_score`, `context_action`, `context_refs`, `time_scope`, `target_date` |
| "tự động trả về FallBack Tool" | Sai — không có fallback tool tự động. Nếu LLM trả 0 tool: in cảnh báo, return list rỗng. `text2cypher` là direct tool Router chủ động chọn |
| Retriever generic 1 dòng đầu vào | Mỗi retriever có pipeline 3 pha CLASSIFY → EXTRACT → EXECUTE; nhiều LLM call/lượt |
| Đầu ra retriever là `List[Dict]` Node+Properties | Thực tế `dict{"contexts": list[str encoded bundle], "debug", "retriever_name", "resolved_query", "cache_status", ...}` |
| Không có direct tool | Có 3 direct tool; `clarify` và `respond` là **exclusive** |
| Không có Response LLM | Có — `_stream_answer` gọi `chat_stream` (gpt-4.1) |
| Không có cache reuse | Có `validate_reuse_request` 5 luật deterministic |
| Không có khôi phục phiên | `on_chat_resume` + `restore_conversation_state` |

### §4.4.1 Sơ đồ luồng end-to-end (thay sơ đồ 5 bước cũ)

**Hình**: swimlane 4 lane: `User` / `Presentation (Chainlit hook)` / `Application (Router + memory + bundle)` / `Adapter (LLM API, Neo4j, Postgres data layer)`.

**Bảng 7 pha xử lý 1 lượt chat**:

| Pha | Vị trí | Đầu vào | Đầu ra |
|---|---|---|---|
| 1. Tiếp nhận & chuẩn bị | `presentation/main.py::main` | `cl.Message`, session state | `turn_id`, `thread_id`, `kg_version` |
| 2. Xây dựng working_history | `application/conversation_context.py::build_working_history` | `session_history`, `conversation_anchors`, query, budget | `router_history` (token-bounded, có anchor) |
| 3. Định tuyến (Router) | `application/router.py::route_question_with_audit` | working_history + `tool_picker_prompt` + retrieval memory summary + câu hỏi | `tool_calls` (list dict + control fields) |
| 4. Thực thi tool | `application/router.py::handle_tool_calls → _execute_or_reuse_tool_call` | `tool_calls`, `retrieval_memory` | `tool_response` (list dict/string) |
| 5. Cập nhật bộ nhớ | `conversation_context.create_retrieval_memory_entries`, `build_turn_anchor` | `tool_response`, ids | `retrieval_memory_entries`, `turn_anchor` (persist step metadata) |
| 6. Gom & dedupe context | `application/legal_context.py::process_context_strings` + `warning_payload.build_legal_warning_metadata` | `contexts_for_llm` | `ContextPipelineResult` (rendered_text, bundles), `legal_warnings` |
| 7. Sinh đáp án | `presentation/main.py::_stream_answer` + `adapter/config.py::chat_stream` | `main_prompt` + response_history + rendered context + câu hỏi | token stream → `cl.Message` |

**Đoạn diễn giải** (~200 từ): 3 nhánh sớm (`clarify`/`respond` exclusive bỏ qua pha 6+7; `text2cypher` đi pha 6+7); 3 vai LLM riêng biệt (Router/Retriever/Response) với `temperature=0` cho 2 cái đầu; guest và user thật cùng pipeline, khác chỉ ở pha 5.

### §4.4.2 Đặc tả Router Agent (thay bảng cũ)

**Bảng đặc tả chính**:

| Thành phần | Mô tả |
|---|---|
| Chức năng | Phân tích ý định đa lượt, chọn (các) tool retriever hoặc 1 direct tool, sinh metadata điều khiển |
| Vị trí | `application/router.py::route_question_with_audit` |
| Mô hình | `ROUTER_LLM` (config trong `adapter/config.py`), gọi qua LangChain `bind_tools(tool_choice="any")` |
| Đầu vào | (i) `tool_picker_prompt` (system) (ii) `working_history` (iii) "BỘ NHỚ RETRIEVAL KHẢ DỤNG" summary (iv) câu hỏi nguyên văn |
| Tool schema | 20 retriever + 3 direct tool; mỗi schema mở rộng bởi `_with_router_confidence_schema` thêm 5 field control |
| Đầu ra | `list[tool_call]` cấu trúc `{name, args, ...control_fields}` |
| Hậu xử lý | `_unique_tool_calls` dedupe; `_strip_router_only_args` tách control fields khỏi args |
| Validation | LangChain bắt match 1 trong tool_choice; nếu 0 tool, log cảnh báo và trả list rỗng (KHÔNG fallback tự động) |

**Bảng phụ — 5 field control**:

| Field | Kiểu | Vai trò |
|---|---|---|
| `confidence_score` | float [0,1] | Mức độ tự tin của Router |
| `context_action` | `"retrieve"`/`"reuse"` | Gọi mới hay reuse memory |
| `context_refs` | list[str] | UUID entry memory để reuse |
| `time_scope` | `"current"`/`"explicit"`/`"ambiguous"` | Cách nhìn mốc thời gian |
| `target_date` | `"YYYY-MM-DD"`/`"YYYY"` | Mốc thời gian cho time filter Cypher |

**lstinputlisting** (recommended): `tool_picker_prompt` excerpt 15–20 dòng.

**Ghi chú**: `retriever_policy.py` còn tồn tại nhưng đã tắt trong `route_question_with_audit`. KHÔNG mô tả là cổng lọc bắt buộc.

### §4.4.3 Đặc tả Retriever Agent (kiến trúc chung 3 pha)

**Đại diện minh họa**: `adapter/retrievers/ket_hon/dieu_kien_ket_hon.py` (hoặc retriever đã chọn ở §4.3.5).

**Bảng đặc tả**:

| Thành phần | Mô tả |
|---|---|
| Chức năng | Trích xuất căn cứ pháp lý từ Neo4j KG cho 1 chủ đề; trả list bundle đã encode |
| Vị trí | `adapter/retrievers/<topic>/<name>.py` |
| Mô hình | `RETRIEVER_LLM` (config `adapter/config.py`) — 1+ lần/lượt |
| Đầu vào | `query: str` (đã loại control field) |
| Pha 1 — CLASSIFY | 1 LLM call → chọn ≥1 template từ `TemplateRegistry`; Pydantic schema `List[TemplateChoice]` |
| Pha 2 — EXTRACT | 1 LLM call/template → params + `thoi_diem_su_kien`; Pydantic schema động build bởi `build_params_with_date_schema` |
| Pha 3 — EXECUTE | Cypher 2 pha (`EXPAND_AND_TIMEFILTER`) qua `asyncio.to_thread`; gom `Context_Tho` |
| Pha 4 — POST | `encode_context_record` → bundle string `LEGAL_CONTEXT_BUNDLE_V1:...`; `save_lazy_viz_stub` lưu stub viz |
| Đầu ra | `dict{contexts: list[str], debug: str, retriever_name: str, resolved_query: str}` |

**Bảng phụ**: 20 retriever × số template × term_mapping fields (trích từ `retriever_catalog.TERM_MAPPING_TRIGGER_SOURCES` và `cypher-template-index.md` — auto). Chạy `sync-thesis-context.ps1` để cập nhật trước khi viết.

**Đoạn ghi chú**: trạng thái mixed-compatible — một số retriever còn trả legacy text qua `chuan_hoa_Context_cho_LLM`; `process_context_strings` chấp nhận cả hai.

**lstinputlisting** (recommended): 3 đoạn nhỏ — CLASSIFY (Pydantic `TemplateChoice`), EXTRACT (build_params_with_date_schema), EXECUTE (chữ ký entry function).

### §4.4.4 Đặc tả Direct Tools

**Bảng đặc tả 3 direct tool**:

| Tool | Vị trí | Tính chất | Khi nào Router chọn |
|---|---|---|---|
| `clarify` | `adapter/direct_tools.py::clarify_question` | **Exclusive** — bỏ qua mọi tool khác + pha 6+7 | Follow-up có ≥2 cách hiểu hợp lý |
| `respond` (`answer_given`) | `adapter/direct_tools.py::answer_given` | **Exclusive** | Câu trả lời đã có trong working_history hoặc user chitchat |
| `text2cypher` | `adapter/direct_tools.py::text2cypher` → `adapter/text2cypher.py::Text2Cypher` | KHÔNG exclusive — đi pha 6+7 | Không retriever chuyên biệt phù hợp (fallback) |

**Cơ chế exclusive**: `presentation/main.py` dòng 538–553 — nếu `len(tool_response)==1` và phần tử đầu là string (không phải dict có `contexts`), bỏ qua `process_context_strings` và Response LLM, gửi thẳng string.

### §4.4.5 Đặc tả Response LLM (Tổng hợp đáp án)

**Bảng đặc tả**:

| Thành phần | Mô tả |
|---|---|
| Chức năng | Tổng hợp câu trả lời tự nhiên dựa trên căn cứ pháp lý đã dedupe; streaming token |
| Vị trí | `presentation/main.py::_stream_answer` + `adapter/config.py::chat_stream` |
| Mô hình | `RESPONSE_LLM` (gpt-4.1) |
| Đầu vào | `main_prompt` (system) + `response_history` (budget `RESPONSE_HISTORY_MAX_TOKENS`) + system msg rendered context + câu hỏi nguyên văn & đã giải nghĩa |
| Đầu ra | Stream token vào `cl.Message`; append `session_history` |
| Xử lý lỗi | Catch Exception khi `chat_stream` lỗi kết nối → stream câu xin lỗi fallback |
| Bỏ qua khi | Router trả direct exclusive (`clarify`/`respond`) |
| Metadata bổ sung | `legal_warnings` từ `build_legal_warning_metadata` gắn vào `msg.metadata` |

**Đoạn diễn giải**: nhấn mạnh đây là **bước sinh đáp án**, không phải agent có khả năng gọi tool — RESPONSE_LLM không `bind_tools`. UI có step "Tổng hợp đáp án" trong expert mode.

### §4.4.6 Cơ chế cache reuse retriever

**Bảng 5 luật deterministic validation** (`application/conversation_context.py::validate_reuse_request`):

| # | Luật | Lý do |
|---|---|---|
| 1 | `context_ref` tồn tại trong `retrieval_memory` đúng `thread_id` | Không cross-thread reuse |
| 2 | `retriever_name` của entry trùng tool đang gọi | Cùng schema bundle |
| 3 | `kg_version` của entry trùng `current_kg_version()` | KG đã đổi → invalidate |
| 4 | `target_date` + `is_user_provided_date` của bundle khớp `time_scope` | Cùng mốc thời gian |
| 5 | Encoded bundle parse được & `process_context_strings` merge được | Bảo toàn schema codec |

**Hành vi**:
- Pass cả 5 → `_reuse_tool_call` trả dict với `cache_status="reused"`, `context_refs_used`. UI step `Retriever cache: <name>` (vs `Retriever: <name>` cho execute)
- Fail 1+ → fallback execute thật, gắn `cache_fallback_reason`

**Hình**: sequence diagram nhỏ — Router LLM đặt `context_action="reuse"` → `_execute_or_reuse_tool_call` → `validate_reuse_request` → 5 luật → reuse path hoặc fallback.

### §4.4.7 Khôi phục phiên hội thoại (resume)

**Bảng quy trình**:

| Bước | Vị trí | Việc |
|---|---|---|
| 1. Sidebar click thread cũ | Chainlit frontend | Gọi `on_chat_resume(thread)` |
| 2. Load steps Postgres | thư viện `chainlit` | `ThreadDict.steps` chứa metadata từ pha 5 lượt cũ |
| 3. Restore in-memory | `main.py::on_chat_resume` → `conversation_context.restore_conversation_state` | Tái tạo `session_history`, `retrieval_memory`, `conversation_anchors` |
| 4. Restore compare actions | `compare_actions.restore_compare_actions_from_thread` | Gắn lại Action button |
| 5. Re-send chat settings | `_send_chat_settings()` | Đồng bộ expert mode toggle |

**Đoạn diễn giải**: nếu `kg_version` lưu trong step khác `current_kg_version()`, entry memory restored tự bị invalidate ở luật #3 khi Router thử reuse. Guest KHÔNG vào nhánh này vì `GuestAwareSQLAlchemyDataLayer.create_step` trả `None` — không có step cũ để restore.

---

## Việc cần làm theo thứ tự

| TT | Việc | Bạn / Agent |
|---|---|---|
| 1 | Đọc plan này, xác nhận scope | Bạn |
| 2 | Xóa dòng 168–265 (toàn bộ "Thiết kế lớp" + biểu đồ trình tự use case tư vấn pháp lý + comment use case khôi phục) | Agent |
| 3 | Viết §4.3 mới (7 sub-subsection) | Agent |
| 4 | Viết §4.4 mới (7 sub-subsection) | Agent |
| 5 | Tạo 6 file `.drawio` cho §4.3 + 2 file `.drawio` cho §4.4 trong `Hinhve/Thiet_ke_chi_tiet_goi/` và `Hinhve/Agentic_Workflow_chi_tiet/` | Agent |
| 6 | Export `.drawio` → `.png` 200 DPI | Bạn |
| 7 | Cập nhật `\lstinputlisting` (5–7 đoạn ≤30 dòng/đoạn) | Agent |
| 8 | Build PDF kiểm tra `\ref{}` | Bạn chạy `scripts/build-thesis.ps1` |

## Lưu ý workspace rule

- Tên quan hệ Neo4j: `CO_DIEU`, `CO_KHOAN`, `CO_DIEM`, `THAM_CHIEU_DEN`, `DUOC_SUA_DOI_BOI` (không phải `SUA_DOI_BOI`), `HUONG_DAN_BOI`, `THAY_THE_BOI`, `BAI_BO_BOI`.
- Số retriever: **20**. Direct tool: **3** (`clarify`, `respond`, `text2cypher`). `clarify`/`respond` là direct response exclusive.
- KHÔNG mô tả `RetrieverPolicy` là filter production bắt buộc.
- KHÔNG mô tả `application/query_updater.py` là flow chính.
- KHÔNG mô tả `adapter/obsolete_retrievers/`.
- KHÔNG tuyên bố mọi retriever đã migrate sang bundle — trạng thái hiện tại mixed-compatible.
- Kiểm tra `\lstinputlisting` compile được + workspace rule "Code thực tế > mô tả cũ trong .tex nếu lệch nhau".
