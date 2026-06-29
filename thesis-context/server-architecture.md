# Kiến trúc server đích — Router + Subagents pattern

Tài liệu này mô tả kiến trúc mục tiêu sau khi server được refactor vào cây
mới `server/` theo pattern multi-agent **Router (top-level) + Subagents
(mid-level)** đề xuất bởi bài viết [Choosing the Right Multi-Agent
Architecture](https://www.langchain.com/blog/choosing-the-right-multi-agent-architecture)
của LangChain. Tài liệu giữ vai trò nguồn sự thật khi viết Chương 4 đồ án
và khi refactor code thật ở các phase sau.

Tài liệu chỉ mô tả phần server; phần client là `frontend/` (Chainlit React
fork) giữ nguyên, kết nối qua socket.io như hiện tại.

## Lý do chọn pattern

Bài viết của LangChain liệt kê bốn pattern cơ bản. Khi đối chiếu với
codebase hiện tại, **Router pattern** là lựa chọn khớp nhất vì:

- Chatbot có 20 miền pháp lý độc lập (cấp dưỡng, đăng ký kết hôn, chia
  tài sản sau ly hôn, xử phạt vi phạm, ...) — đúng định nghĩa "distinct
  verticals" mà bài viết khuyến nghị Router.
- Mỗi câu hỏi của người dùng thường chạm vào nhiều miền cùng lúc; cần
  fan-out song song để giảm độ trễ tổng thể. Trong các đo lường của
  LangChain, Router cùng Subagents là hai pattern duy nhất đạt mức năm
  sao cho song song hoá.
- Mỗi miền có ngữ cảnh Cypher template riêng và mong muốn cô lập ngữ
  cảnh khỏi nhau để tránh nhiễm chéo, đúng điểm mạnh của Subagents.
- Bộ nhớ `retrieval_memory` và `conversation_anchors` đã sẵn có; bài
  viết khuyến nghị: khi Router cần trạng thái thì bọc Router bằng một
  lớp có trạng thái. Hệ thống chọn biến thể **external state management**
  (deterministic) thay vì **tool wrapper** (LLM-driven): lớp
  `ConversationOrchestrator` giữ session state nhưng không có model riêng;
  mọi quyết định thông minh tập trung ở `RouterAgent` và các subagent.

Pattern mid-level — Subagents — được áp dụng bên trong mỗi retriever:
một classifier LLM chọn 1-3 Cypher template, mỗi template được trích
xuất tham số bởi một LLM nhỏ, rồi chạy Cypher song song. Cấu trúc này
cũng đúng định nghĩa Subagents (supervisor tập trung điều phối các
subagent stateless để trả về kết quả tổng hợp).

## Bản đồ gói

```
server/
    app/                       Lớp ứng dụng Chainlit
        main.py                Các hook on_chat_start / on_chat_resume / on_message / oauth_callback
        routes/
            guest_auth.py      Endpoint /auth/guest và middleware chặn guest quản lý hội thoại
            projects.py        REST /project/projects, /project/threads
            viz.py             /viz/{id} render snapshot đồ thị tri thức

    conversation/
        orchestrator.py    ConversationOrchestrator — điều phối phiên (không LLM)
        memory.py          retrieval_memory_summary, validate_reuse_request, build_turn_anchor, restore_conversation_state
        history.py         build_working_history, ngân sách token cho Router / Response

    agents/
        base.py                Agent ABC, TypedDict RetrieverResult / ToolCall
        router/
            agent.py           RouterAgent decide() + dispatch() song song
            prompt.py          tool_picker_prompt
            schema.py          Tô điểm schema với confidence_score / context_action / context_refs / time_scope / target_date
            reuse.py           Cơ chế reuse + render context cho UI
            catalog.py         RetrieverSpec, TriggerRule, 20 RETRIEVER_SPECS
            tool_factory.py    build_presentation_tools — gắn description + callable
        retrievers/
            base.py            RetrieverAgent ABC: classify / extract / execute / run
            _descriptions.py   Map name → module path để Router thấy đầy đủ description
            _shared/           _context_tho_common, _runtime_dates
            cap_duong.py       CapDuongRetriever
            dieu_kien_ket_hon.py
            dang_ky_ket_hon.py
            ket_hon_trai_phap_luat.py
            chung_song_nhu_vo_chong.py
            che_do_tai_san_cua_vo_chong.py
            quyen_nghia_vu_vo_chong.py
            dai_dien_trach_nhiem_vo_chong.py
            quy_dinh_chung_ly_hon.py
            chia_tai_san_sau_ly_hon.py
            cha_me_con_sau_ly_hon.py
            xac_dinh_cha_me_con.py
            quyen_nghia_vu_cha_me_con.py
            tai_san_rieng_cua_con.py
            han_che_quyen_cha_me_con_chua_thanh_nien.py
            hon_nhan_cham_dut_do_vo_chong_chet.py
            quan_he_hon_nhan_co_yeu_to_nuoc_ngoai.py
            quan_he_giua_cac_thanh_vien_khac_trong_gia_dinh.py
            xu_phat_vi_pham.py
            quy_dinh_chung_khai_niem_phap_ly.py
        synthesizer/
            agent.py           SynthesizerAgent.stream, main_prompt
        direct/
            respond.py         RespondAgent (answer_given)
            clarify.py         ClarifyAgent (clarify_question)

    domain/
        legal/
            bundle.py          LegalContextBundle, process_context_strings, merge, dedupe
            codec.py           encode / decode LEGAL_CONTEXT_BUNDLE_V1
            render.py          chuan_hoa_Context_cho_LLM
            warnings.py        build_legal_warning_metadata
        conversation/
            types.py           Kiểu Turn, Anchor, MemoryEntry, RetrievalMemory

    infrastructure/
        llm/
            factory.py         build_router_llm / build_retriever_llm / build_response_llm
            streaming.py       chat_stream với retry
        neo4j/
            client.py          driver Neo4j, env URI/USER/PASS
            cypher_templates/  Toàn bộ hierarchy theo 20 miền
        persistence/
            data_layer.py      GuestAwareSQLAlchemyDataLayer
            projects.py        ProjectStore CRUD
            guest.py           is_guest_user, create_persisted_guest, GUEST_IDENTIFIER_PREFIX
            init_db.py
        viz/
            snapshot_store.py  resolve_viz_snapshot, save_lazy_viz_stub, load_snapshot

    interface/
        router_tools.py        OpenAI tool schema cho Router LLM (catalog → schema thuần)
        direct_tools.py        Schema clarify / respond

    shared/
        phrase_match.py        prepare_question, match_phrase_groups
        datetime_vn.py         chuan_hoa_thoi_diem_su_kien, _format_date_vn
```

## Quy tắc phụ thuộc giữa các tầng

Chỉ tầng trên được phép phụ thuộc tầng dưới, mỗi mũi tên trong biểu đồ
gói thể hiện một quan hệ import.

```
app  ──▶  conversation  ──▶  agents  ──▶  domain
                              ──▶  infrastructure  ──▶  shared
                              ──▶  interface
       ──▶  infrastructure (chỉ ở app.routes cho data layer + viz)
```

Không gói nào được import ngược tầng. Trong nội bộ `conversation/`:

- `orchestrator` phụ thuộc `agents.router`, `agents.synthesizer`, và
  `domain.legal` (merge/dedupe context).

Trong nội bộ `agents/`:
  `direct`, và `domain.legal` (render context cho UI).
- `retrievers` phụ thuộc `infrastructure.neo4j` và `infrastructure.llm`,
  cùng `domain.legal.codec` để mã hoá bundle.
- `synthesizer` phụ thuộc `infrastructure.llm` và `domain.legal.render`.
- `direct` không phụ thuộc retriever; hai tác tử này trả phản hồi
  trực tiếp.

## Phân cấp lớp

```
ConversationOrchestrator        (stateful, deterministic — KHÔNG kế thừa Agent)

Agent (ABC)
├── RouterAgent                 (stateless, tool calling, fan-out)
├── SynthesizerAgent            (stream Response LLM)
├── RetrieverAgent (ABC)
│   ├── CapDuongRetriever
│   ├── DieuKienKetHonRetriever
│   ├── DangKyKetHonRetriever
│   ├── KetHonTraiPhapLuatRetriever
│   ├── ChungSongNhuVoChongRetriever
│   ├── CheDoTaiSanCuaVoChongRetriever
│   ├── QuyenNghiaVuVoChongRetriever
│   ├── DaiDienTrachNhiemVoChongRetriever
│   ├── QuyDinhChungLyHonRetriever
│   ├── ChiaTaiSanSauLyHonRetriever
│   ├── ChaMeConSauLyHonRetriever
│   ├── XacDinhChaMeConRetriever
│   ├── QuyenNghiaVuChaMeConRetriever
│   ├── TaiSanRiengCuaConRetriever
│   ├── HanCheQuyenChaMeConChuaThanhNienRetriever
│   ├── HonNhanChamDutDoVoChongChetRetriever
│   ├── QuanHeHonNhanCoYeuToNuocNgoaiRetriever
│   ├── QuanHeGiuaCacThanhVienKhacTrongGiaDinhRetriever
│   ├── XuPhatViPhamRetriever
│   └── QuyDinhChungKhaiNiemPhapLyRetriever
├── RespondAgent                (direct, exclusive)
└── ClarifyAgent                (direct, exclusive)
```

`ConversationOrchestrator` **kết tập** (composition) một `RouterAgent` và
một `SynthesizerAgent`; nó không phải tác tử LLM-driven theo nghĩa hẹp
trong bài LangChain.

## Lifecycle một lượt — ConversationOrchestrator

Khi người dùng gửi một message, ConversationOrchestrator điều phối tám bước
sau (`server/conversation/orchestrator.py`, được gọi từ Chainlit hook trong
`server/app/main.py`):

1. Đọc `session_history`, `retrieval_memory`, `conversation_anchors` từ
   Chainlit user session; sinh `turn_id` mới và lấy `thread_id`.
2. Gọi `history.build_working_history` để dựng prompt history rút gọn
   theo ngân sách `ROUTER_HISTORY_MAX_TOKENS`.
3. Gọi `RouterAgent.decide` với câu hỏi + history + tóm tắt bộ nhớ;
   Router LLM trả về danh sách tool call duy nhất theo tên.
4. Gọi `RouterAgent.dispatch` chạy song song các retriever bằng
   `asyncio.gather`; với tool call yêu cầu reuse, dispatch chạy
   `validate_reuse_request` deterministic trước khi trả bundle cũ.
5. Cập nhật `retrieval_memory` bằng `create_retrieval_memory_entries`,
   cập nhật `conversation_anchors` bằng `build_turn_anchor`.
6. Trộn ngữ cảnh nhiều retriever qua `domain.legal.bundle.process_context_strings`
   để dedupe căn cứ pháp lý theo khóa `(id, amendment_id, effective_from,
   effective_until)`.
7. Dựng `main_prompt` + history + context và gọi `SynthesizerAgent.stream`;
   nếu Router trả về direct tool (`respond`, `clarify`) thì bỏ qua bước
   này và gửi thẳng văn bản từ tool.
8. Ghi `session_history` mới, gắn metadata (`retrieval_memory_entries`,
   `turn_anchor`, `kg_version`, `legal_warnings`) vào message, và gửi
   tới UI.

## Pattern điểm cố định — sao gọi là Router?

Pattern Router trong bài LangChain định nghĩa: "Router decomposes the
query, invokes zero or more specialized agents in parallel, and synthesizes
results into a coherent response." Bốn thuộc tính dưới đây của thiết kế
khớp chính xác:

- **Decompose**: `RouterAgent` không tự trả lời, nó chỉ phân giải câu
  hỏi thành tập tool call. Nhiệm vụ "có giá trị" được uỷ thác cho
  retriever và synthesizer.
- **Parallel fan-out**: `asyncio.gather` các retriever; mỗi retriever
  có context window riêng, không nhiễm chéo.
- **Synthesize**: `SynthesizerAgent` nhận ngữ cảnh đã hợp nhất, trả lời
  duy nhất một câu trả lời. Khi nhiều retriever cùng trả các điều luật
  trùng nhau, lớp `domain.legal.bundle` lo dedupe trước khi synthesizer
  thấy.
- **Wrapped in stateful layer**: bài viết cảnh báo Router thuần
  stateless không lưu lịch sử; do đó `ConversationOrchestrator` ở trên
  là lớp bọc deterministic có trạng thái (external state management),
  vẫn giữ pattern Router làm thành phần chính.

Bên trong mỗi retriever ta lại thấy pattern Subagents thu nhỏ: classifier
LLM là supervisor, mỗi Cypher template là một subagent stateless, kết
quả Cypher được tổng hợp thành một `RetrieverResult` duy nhất.

## So sánh ngắn với ba pattern khác

| Pattern | Có khớp không | Lý do |
|---|---|---|
| Router | Có | 20 miền độc lập, cần parallel + synthesize, tài liệu khuyến nghị cùng kịch bản. |
| Subagents | Khớp ở mid-level | Mỗi retriever có classifier điều phối 1-3 template stateless; pattern này được áp dụng bên trong, không ở top-level. |
| Skills | Không phù hợp | Skills là một agent đơn nạp prompt theo nhu cầu. Codebase muốn isolation context và parallel — không phù hợp. |
| Handoffs | Không phù hợp | Không có chuyển giao tuần tự giữa các retriever; mỗi lượt là một lần định tuyến + fan-out. |

## Quy ước đặt tên & ràng buộc khi refactor

Khi chuyển 20 retriever sang class, áp dụng quy tắc đặt tên sau để
đảm bảo nhất quán giữa code, schema OpenAI, và tài liệu đồ án:

- Tên class: PascalCase theo tên file, hậu tố `Retriever`. Ví dụ
  `cap_duong.py` → `CapDuongRetriever`.
- Tên tool trong tool calling: giữ snake_case như code hiện tại
  (`cap_duong`, `dieu_kien_ket_hon`, ...). Đây là `Agent.name`.
- Mỗi class export một module-level alias dạng `cap_duong =
  CapDuongRetriever().run` để các shim cũ ở `adapter/retrievers/cap_duong.py`
  vẫn re-export được hàm cùng chữ ký.
- `Agent.run` luôn là async; mọi side effect Neo4j hay LLM nằm trong
  `infrastructure/`.

## Tài liệu liên quan

- `thesis-context/architecture.md`: kiến trúc hiện tại trước refactor.
- `thesis-context/chat-flow.md`: luồng chat / guest / dedupe hiện tại.
- `thesis-context/ch05-code-map.md`: map Chương 5 → file code.
- Plan refactor: `.cursor/plans/refactor-server-router-subagents_dfddf704.plan.md`.
