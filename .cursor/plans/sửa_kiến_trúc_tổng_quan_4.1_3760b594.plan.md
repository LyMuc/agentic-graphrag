---
name: sửa kiến trúc tổng quan 4.1
overview: "Đồng bộ Hình \"Kiến trúc tổng quan\" và đoạn mô tả 17–19 của §4.1 với codebase: đổi tên \"Main Agent\" → \"Main Orchestrator\", chỉnh nhãn input/output các mũi tên cho khớp `presentation/main.py` + `application/router.py`, và viết lại text frontend/backend để phản ánh React frontend + guest bootstrap, 2 lần gọi LLM (Router + Response), guest không persist."
todos:
  - id: redraw_diagram
    content: Vẽ lạ `Hinhve/Kiến trúc tổng quan.png` trong draw.io theo spec §A (đổi tên Main Agent → Main Orchestrator, chỉnh nhãn in/out, cân nhắc thêm 2 mũi tên LLM)
    status: pending
  - id: rewrite_line17_frontend
    content: "Viết lạ đoạn 17 (Frontend) theo §B.2: React custom + guest bootstrap + HTTP/WebSocket"
    status: pending
  - id: rewrite_line19_backend
    content: "Viết lạ đoạn 19 (Backend) theo §B.3: đổi (i) Main Orchestrator, cập nhật (ii)–(v), thêm ghi chú 3 vị trí gọi LLM"
    status: pending
  - id: sync_section_4_4
    content: "Đổi đồng bộ tên Main Agent → Main Orchestrator ở §4.4 (Bảng `table: main_agent`, dialogue dòng 67) hoặc ghi nhố để sửa ở vòng tiếp theo"
    status: pending
  - id: build_thesis
    content: Build thử `scripts/build-thesis.ps1` và kiểm tra PDF ở `build/DoAn.pdf`
    status: pending
isProject: false
---

# Sửa Hình "Kiến trúc tổng quan" và mô tả §4.1 (`4_Ket_qua_thuc_nghiem.tex` dòng 4–19)

## Phạm vi

- File LaTeX: [`ĐATN_.../Chuong/4_Ket_qua_thuc_nghiem.tex`](ĐATN_20225919_Lê_Thái_Sơn_Chatbot_tư_vấn_luật_hôn_nhân_gia_đình/Chuong/4_Ket_qua_thuc_nghiem.tex) dòng 4–19 (`\section{Thiết kế kiến trúc}` → hết đoạn mô tả).
- Hình draw.io: [`Hinhve/Kiến trúc tổng quan.png`](ĐATN_20225919_Lê_Thái_Sơn_Chatbot_tư_vấn_luật_hôn_nhân_gia_đình/Hinhve/Kiến trúc tổng quan.png) — sinh viên tự vẽ lại theo spec dưới.
- Code đối chiếu (không sửa): [`presentation/main.py`](presentation/main.py), [`application/router.py`](application/router.py), [`application/conversation_context.py`](application/conversation_context.py), [`application/legal_context.py`](application/legal_context.py), [`presentation/guest_auth.py`](presentation/guest_auth.py), [`adapter/data_layer.py`](adapter/data_layer.py), [`frontend/src/AppWrapper.tsx`](frontend/src/AppWrapper.tsx).

## A. Hình "Kiến trúc tổng quan" — spec vẽ lại bằng draw.io

Giữ nguyên cấu trúc cụm (Frontend / Backend / dữ liệu), chỉ đổi 1 tên khối và sửa nhãn các mũi tên.

### A.1. Đổi tên khối

- `Main Agent` → **`Main Orchestrator`** (hoặc `Chat Orchestrator`). Lý do: hàm `main()` trong `presentation/main.py:643` được decorate `@cl.on_message`, chỉ chạy pipeline tuần tự `build_working_history → route_question_with_audit → process_context_strings → chat_stream`, không có decision loop / autonomy → không phải Agent.
- `Retriever Router Agent` → **`Router Agent`** (rút gọn cho khớp tên module `application/router.py`).
- Các khối khác giữ nguyên: `User (Actor)`, `Chatbot Web UI`, `Server-Backend`, `API LLM`, `Retriever Agents`, `Knowledge Graph`, `Persistent Session Storage`.

### A.2. Sửa nhãn input/output các mũi tên (theo code thực tế)

- `User (Actor) → Chatbot Web UI`: giữ "Request" (hoặc đổi "Câu hỏi").
- `Chatbot Web UI ↔ Server-Backend` (HTTP/WebSocket): đổi nhãn để gồm 2 mạch:
  - "HTTP `/auth/guest` (bootstrap guest JWT)" — phản ánh `frontend/src/AppWrapper.tsx` gọi `POST /auth/guest` khi chưa login (xem `presentation/guest_auth.py`).
  - "WebSocket Chainlit (message stream)".
- `Server-Backend → Persistent Session Storage`: đổi "Session read/write" → **"Session read/write (chỉ user đăng nhập; guest bỏ qua)"**. Lý do: `adapter/data_layer.py` `GuestAwareSQLAlchemyDataLayer` trả `None` cho các `create_step/update_step/...` của guest (`chat-flow.md` dòng 44).
- `Server-Backend ↔ Main Orchestrator`: đổi:
  - Vào: "Câu hỏi của user + thread\_id".
  - Ra: "Câu trả lời cuối (stream) + metadata trace".
- `Main Orchestrator ↔ API LLM` (Response LLM): đổi nhãn:
  - Vào: "Prompt hệ thống + Context đã chuẩn hóa + working\_history".
  - Ra: "Stream token câu trả lời".
  Lý do: `presentation/main.py:732-744` build `llm_messages = [main_prompt, *response_history, user_query]` rồi gọi `chat_stream` streaming.
- `Main Orchestrator ↔ Router Agent`:
  - Vào: "Câu hỏi + router\_history + retrieval\_memory".
  - Ra: "tool\_response (list contexts)".
  Lý do: `presentation/main.py:554-561` gọi `route_question_with_audit(updated_question, tools, router_history, retrieval_memory=..., thread_id=..., kg_version=...)`.
- `Router Agent ↔ Retriever Agents`:
  - Vào: "tool\_calls (tên retriever + params, có thể song song)".
  - Ra: "contexts dạng `LEGAL_CONTEXT_BUNDLE_V1` hoặc text".
  Lý do: Router LLM trả `tool_calls`, Server chạy song song retriever; retriever đã migrate trả bundle, chưa migrate trả text legacy (`chat-flow.md` dòng 176–180).
- `Retriever Agents ↔ Knowledge Graph`: giữ "Cypher query" / "Context (List[Dict] nút + thuộc tính)".
- **Thêm 2 mũi tên LLM** (vì hình đang ngầm chỉ có Main Orchestrator gọi LLM, không phản ánh Agentic):
  - `Router Agent ↔ API LLM` — nhãn "Tool-picking prompt + tool schema" / "tool\_calls JSON".
  - `Retriever Agents ↔ API LLM` — nhãn "Prompt trích intent + params" / "intent + params Cypher".

### A.3. Cần xác nhận thêm

- Có muốn vẽ thêm 2 mũi tên LLM (mục cuối A.2) hay không? Nếu giữ tối giản tuyệt đối thì bỏ và chỉ mô tả trong text.

## B. Viết lại đoạn mô tả `4_Ket_qua_thuc_nghiem.tex` dòng 17 và 19

### B.1. Câu hỏi 1 trong text (caption hình)

Caption ở dòng 13 (`\caption{Kiến trúc tổng quan của hệ thống}`) giữ nguyên.

### B.2. Đoạn 17 (Frontend) — đề xuất bản viết lại

> Phía frontend là một ứng dụng web React tùy biến trên transport của Chainlit, cung cấp giao diện chat, hiển thị luồng xử lý của các tác nhân và quản lý phiên hội thoại. Khi người dùng chưa đăng nhập, frontend tự động gọi `POST /auth/guest` để backend cấp JWT `guest:<uuid>`, cho phép sử dụng chatbot ngay mà không bắt buộc đăng nhập; tuy nhiên các thao tác quản lý lịch sử/hội thoại/feedback sẽ bị ẩn và không được lưu trữ bền vững. Frontend duy trì kết nối HTTP/WebSocket với backend để gửi câu hỏi và nhận stream câu trả lời cùng metadata truy vết.

Lý do: khớp `frontend/src/AppWrapper.tsx`, `presentation/guest_auth.py`, `adapter/data_layer.py`.

### B.3. Đoạn 19 (Backend) — đề xuất bản viết lại

Giữ cấu trúc liệt kê (i)–(v), chỉ đổi nội dung từng mục:

- (i) **Main Orchestrator**: tầng điều phối hội thoại trong `presentation/main.py` (hook `on_message`). Mỗi lượt hỏi, orchestrator dựng `working_history`, gọi Router Agent, gom context từ các Retriever Agents, sau đó gọi Response LLM để sinh câu trả lời theo prompt pháp lý chuyên biệt.
- (ii) **Router Agent**: tác nhân định tuyến dựa trên LLM, phân tích câu hỏi và lịch sử rút gọn để chọn một hoặc nhiều retriever phù hợp trong số 20 retriever pháp lý của hệ thống và 3 công cụ trực tiếp (`clarify`, `respond`, `text2cypher`); đồng thời quyết định reuse context cũ hay gọi retriever mới.
- (iii) **Retriever Agents**: các tác nhân truy xuất chuyên biệt cho từng dạng câu hỏi pháp lý. Mỗi retriever sử dụng LLM để trích xuất intent và tham số, sinh truy vấn Cypher theo template, chạy trên Knowledge Graph và trả về căn cứ pháp lý kèm thông tin hiệu lực, sửa đổi, hướng dẫn.
- (iv) **Knowledge Graph**: đồ thị tri thức Luật Hôn nhân và Gia đình 2014 lưu trên Neo4j, mô hình hóa văn bản pháp luật theo cấu trúc Điều–Khoản–Điểm cùng các quan hệ pháp lý (`CO_DIEU`, `THAM_CHIEU_DEN`, `DUOC_SUA_DOI_BOI`, `HUONG_DAN_BOI`, `THAY_THE_BOI`, `BAI_BO_BOI`).
- (v) **Persistent Session Storage**: PostgreSQL lưu trữ lịch sử hỏi đáp, input/output các agent, context truy xuất, câu trả lời cuối và metadata truy vết (retrieval memory, turn anchor, KG version) phục vụ resume hội thoại và đánh giá hệ thống. Người dùng guest sử dụng cùng pipeline trong bộ nhớ phiên Chainlit nhưng **không** được ghi xuống PostgreSQL.

Ghi chú thêm về luồng gọi LLM (có thể chèn 1 câu cuối đoạn 19 hoặc tách thành đoạn nhỏ):

> Trong một lượt hỏi, hệ thống gọi API LLM ở ba vị trí: Router LLM (tool-picking ở Router Agent), Retriever LLM (trích intent/params ở từng Retriever Agent đang được kích hoạt) và Response LLM (tổng hợp đáp án ở Main Orchestrator).

## C. Đối chiếu với mô tả §4.4 (đảm bảo nhất quán)

- §4.4 dòng 67 và Bảng `table: main_agent` (dòng 75–88) đang gọi "Main Agent". Khi đổi tên ở §4.1, **bắt buộc đổi đồng bộ** ở §4.4 và các bảng đặc tả (label `table: main_agent`, caption "Đặc tả Tác nhân Điều phối (Main Agent)") để tránh lệch thuật ngữ. Nếu chọn `Main Orchestrator` thì label/caption nên là "Đặc tả tầng Điều phối (Main Orchestrator)".
- Quy mô retriever: hiện code có **20 retriever + 3 direct tool**, đảm bảo các đoạn §4.4 phản ánh đúng con số này (sẽ xử lý ở phần sửa tiếp theo của bạn, không thuộc dòng 4–19).

## D. Checklist sau khi sửa

- [ ] Hình mới đã được export PNG và lưu vào `Hinhve/Kiến trúc tổng quan.png` (cùng path để không phải đổi `\includegraphics`).
- [ ] Caption + nội dung 17 và 19 trong `.tex` đã viết lại theo §B.
- [ ] Đổi tên `Main Agent` → `Main Orchestrator` đồng bộ ở §4.4 (Bảng `table: main_agent`) hoặc note rõ rằng sẽ sửa ở vòng tiếp theo.
- [ ] Build thử bằng `powershell -File scripts/build-thesis.ps1`.