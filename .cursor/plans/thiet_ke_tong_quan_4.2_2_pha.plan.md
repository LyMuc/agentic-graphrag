---
name: §4.2 Thiết kế tổng quan — 2 pha (refactor + tài liệu)
overview: Đồng bộ §4.2 "Thiết kế tổng quan" với codebase. Pha 1 (Composer 2.5) thực hiện refactor tối thiểu (Phương án A) để code khớp với sơ đồ 4 gói layered. STOP sau pha 1 để sinh viên test. Pha 2 (Opus 4.7) vẽ lại 2 sơ đồ gói (server + client) và viết lại §4.2 trong LaTeX.
todos:
  - id: phase1-rename-direct-tools
    content: "P1.1 — Tạo adapter/direct_tools.py (chuyển nội dung từ utils/general.py); cập nhật import ở presentation/main.py (line 83-90), application/retriever_catalog.py (nếu có), tests"
    status: pending
  - id: phase1-extract-codec
    content: "P1.2 — Tạo utils/legal_context_codec.py (hoặc domain/legal_context_codec.py) thuần dữ liệu chứa encode_context_record/decode_context_record; application/legal_context.py re-export để giữ tương thích; sửa import ở 20 file adapter/retrievers/*"
    status: pending
  - id: phase1-retriever-registry
    content: "P1.3 — Đảm bảo application/retriever_catalog.RETRIEVER_SPECS export đủ (name, fn, description); cập nhật presentation/main.py để import 1 list duy nhất thay vì 20+ retriever rời"
    status: pending
  - id: phase1-delete-old
    content: "P1.4 — Xóa utils/general.py sau khi không còn nơi nào import; xác nhận utils/ chỉ còn utils.py thuần (pydantic, re, datetime)"
    status: pending
  - id: phase1-verify
    content: "P1.5 — Chạy pytest -q; smoke test 1–2 câu hỏi end-to-end qua Chainlit; xác nhận luồng router/retriever/response không gãy"
    status: pending
  - id: phase1-stop
    content: "🛑 STOP — Sinh viên test thủ công. Composer 2.5 dừng ở đây. Pha 2 do Opus 4.7 thực hiện."
    status: pending
  - id: phase2-confirm
    content: "P2.0 — Opus xác nhận lại với sinh viên: (a) client diagram tách 4.2.1/4.2.2 hay inline?; (b) drawio template style (giống Kiến trúc tổng quan.drawio hay Hình 4.2 mẫu phân màu)"
    status: pending
  - id: phase2-server-drawio
    content: "P2.1 — Tạo Hinhve/Sơ đồ gói server.drawio: 4 gói (presentation top → application → adapter → utils bottom); mũi tên dashed cho dependency, dotted cho usage; chú thích legend"
    status: pending
  - id: phase2-client-drawio
    content: "P2.2 — Tạo Hinhve/Sơ đồ gói client.drawio: 9 gói chính trong frontend/src; phân màu xanh (LeftSidebar) / vàng (api, components/{header, share}, lib, pages, types, AppWrapper) / trắng (state, contexts, hooks, i18n, components/{chat, Elements, ChatSettings, Tasklist, ui})"
    status: pending
  - id: phase2-export-png
    content: "P2.3 — Sinh viên export 2 drawio → PNG (Hinhve/Sơ đồ gói.png ghi đè; Hinhve/Sơ đồ gói client.png mới)"
    status: pending
  - id: phase2-rewrite-tex
    content: "P2.4 — Viết lại §4.2 trong ĐATN_.../Chuong/4_Ket_qua_thuc_nghiem.tex dòng 21–35: tách 4.2.1 (server) + 4.2.2 (client); fix lỗi 'chức→chứa', 'adapters→adapter'; mô tả trách nhiệm chi tiết theo file map"
    status: pending
  - id: phase2-build
    content: "P2.5 — Chạy scripts/build-thesis.ps1; kiểm tra label \\ref{fig:Fig1} và label client mới resolve được; PDF khớp layout"
    status: pending
isProject: false
---

# Thiết kế tổng quan §4.2 — Kế hoạch 2 pha

Tài liệu này tách thành **2 pha riêng biệt** vì sử dụng 2 agent khác nhau (Composer 2.5 cho refactor, Opus 4.7 cho tài liệu). Giữa 2 pha có **điểm dừng bắt buộc** để sinh viên test thủ công.

Tham chiếu chính:
- LaTeX: [`ĐATN_.../Chuong/4_Ket_qua_thuc_nghiem.tex`](ĐATN_20225919_Lê_Thái_Sơn_Chatbot_tư_vấn_luật_hôn_nhân_gia_đình/Chuong/4_Ket_qua_thuc_nghiem.tex) dòng 21–35
- Hình hiện tại: [`Hinhve/Sơ đồ gói.png`](ĐATN_20225919_Lê_Thái_Sơn_Chatbot_tư_vấn_luật_hôn_nhân_gia_đình/Hinhve/Sơ đồ gói.png)
- Code map: [`thesis-context/ch05-code-map.md`](thesis-context/ch05-code-map.md), [`thesis-context/chat-flow.md`](thesis-context/chat-flow.md)
- Hình tham chiếu phong cách: [`Hinhve/Kiến trúc tổng quan.drawio`](ĐATN_20225919_Lê_Thái_Sơn_Chatbot_tư_vấn_luật_hôn_nhân_gia_đình/Hinhve/Kiến trúc tổng quan.drawio)

---

## Bối cảnh — 3 vấn đề trong codebase hiện tại

Đã rà soát import giữa 4 gói (`presentation`, `application`, `adapter`, `utils`). Có **2 vi phạm back-dependency** và **1 vấn đề skip tầng**:

| Vi phạm | Vị trí | Số file |
|---|---|---|
| `utils → adapter` (back-dep) | `utils/general.py` import `adapter.text2cypher`, `adapter.config` | 1 file |
| `adapter → application` (back-dep) | `adapter/retrievers/*` import `application.legal_context.encode_context_record` | 20 file |
| `presentation → adapter` (skip tầng) | `presentation/main.py` import 20+ retriever từ `adapter/retrievers/*` để đăng ký Chainlit tool | 1 file (nhiều dòng) |

Phương án đã chọn: **A — Refactor tối thiểu** (xem chi tiết Pha 1 bên dưới).

---

## PHA 1 — Refactor code (Composer 2.5)

**Mục tiêu pha 1:** Khử 3 vấn đề trên với thay đổi tối thiểu, giữ nguyên hành vi runtime. Không sửa LaTeX, không sửa hình vẽ.

**Quy tắc Composer 2.5 cần tuân thủ:**
- Chỉ sửa code Python trong `presentation/`, `application/`, `adapter/`, `utils/`.
- KHÔNG đụng tới `.tex`, `.drawio`, `.png`.
- KHÔNG đụng tới `extraction/`, `benchmark_dataset/`, `data/`, `viz/`, `frontend/`.
- KHÔNG tạo file mới ngoài 2 file được liệt kê (`adapter/direct_tools.py`, `utils/legal_context_codec.py` hoặc `domain/legal_context_codec.py`).
- Giữ public API: tên hàm `answer_given`, `clarify_question`, `text2cypher` và description dict không đổi.

### P1.1 — Dời `utils/general.py` → `adapter/direct_tools.py`

**Lý do:** `utils/general.py` không phải utility thuần, mà chứa cài đặt 3 Chainlit direct tool. Nó import từ `adapter.text2cypher` và `adapter.config.driver`, tức là *gọi xuống* tầng adapter. Đặt ở `adapter/` mới đúng vai trò.

**Việc cụ thể:**
1. Tạo file [`adapter/direct_tools.py`](adapter/direct_tools.py) với nội dung sao chép từ [`utils/general.py`](utils/general.py) (giữ nguyên cả docstring + description dict).
2. Cập nhật import:
   - [`presentation/main.py`](presentation/main.py) dòng 83–90: đổi `from utils.general import ...` → `from adapter.direct_tools import ...`.
   - Kiểm tra `application/retriever_catalog.py`, `application/router_tool_registry.py`, `application/router.py` xem có nơi nào import `utils.general` không; nếu có thì sửa tương ứng.
   - Tìm trong toàn repo: `rg "from utils.general|utils\.general" --type py` để chắc chắn không sót.
3. Xóa [`utils/general.py`](utils/general.py).

**Kiểm tra:** Sau bước này, `rg "utils.general" --type py` phải trả về 0 kết quả. `utils/` chỉ còn `utils.py` và `__init__.py`.

### P1.2 — Tách `encode_context_record`/`decode_context_record` thành module thuần

**Lý do:** Hiện tại 20 retriever ở `adapter/retrievers/*` đều `from application.legal_context import encode_context_record`. Đây là back-dependency thật. Bản chất `encode_context_record` chỉ đóng gói dict thành chuỗi `LEGAL_CONTEXT_BUNDLE_V1:...` — không phụ thuộc bất kỳ business logic nào của `application/`. Tách ra module thuần dữ liệu để cả `adapter` và `application` cùng dùng được.

**Quyết định vị trí (Composer xác định):**
- **Lựa chọn 1 (ưa thích):** `utils/legal_context_codec.py` — vì codec là utility thuần dữ liệu.
- **Lựa chọn 2:** `domain/legal_context_codec.py` — nếu muốn nhấn mạnh đây là *shared contract* và `domain/` là gói chứa schema dùng chung (hiện chỉ có `db_schema.py`, hoàn toàn có thể mở rộng).

→ Khuyến nghị **Lựa chọn 1** để không tạo thêm gói lạ trong sơ đồ. Nếu chọn 2, phải bổ sung gói `domain` vào sơ đồ §4.2 (việc của Pha 2).

**Việc cụ thể:**
1. Xác định các symbol cần dời: đọc [`application/legal_context.py`](application/legal_context.py), tìm định nghĩa `encode_context_record` và `decode_context_record` (và bất kỳ helper nào chúng phụ thuộc trực tiếp — ví dụ `LEGAL_CONTEXT_BUNDLE_V1` prefix constant).
2. Tạo `utils/legal_context_codec.py` (hoặc `domain/legal_context_codec.py`): chuyển định nghĩa + helper sang. File này chỉ được phép import từ `typing`, `json`, `re`, `pydantic`, `utils.utils` (không import `adapter.*` hoặc `application.*`).
3. Trong [`application/legal_context.py`](application/legal_context.py): xóa định nghĩa cũ, thêm `from utils.legal_context_codec import encode_context_record, decode_context_record` ở đầu file (re-export để các nơi cũ vẫn dùng được nếu muốn).
4. Sửa 20 file `adapter/retrievers/*.py` đổi `from application.legal_context import encode_context_record` → `from utils.legal_context_codec import encode_context_record`. Danh sách 20 file:

```
adapter/retrievers/cap_duong.py
adapter/retrievers/han_che_quyen_cha_me_con_chua_thanh_nien.py
adapter/retrievers/hon_nhan_cham_dut_do_vo_chong_chet.py
adapter/retrievers/ket_hon/chung_song_nhu_vo_chong.py
adapter/retrievers/ket_hon/dang_ky_ket_hon.py
adapter/retrievers/ket_hon/dieu_kien_ket_hon.py
adapter/retrievers/ket_hon/ket_hon_trai_phap_luat.py
adapter/retrievers/ly_hon/cha_me_con_sau_ly_hon.py
adapter/retrievers/ly_hon/chia_tai_san_sau_ly_hon.py
adapter/retrievers/ly_hon/quy_dinh_chung_ly_hon.py
adapter/retrievers/quan_he_giua_cac_thanh_vien_khac_trong_gia_dinh.py
adapter/retrievers/quan_he_giua_vo_va_chong/che_do_tai_san_cua_vo_chong.py
adapter/retrievers/quan_he_giua_vo_va_chong/dai_dien_trach_nhiem_vo_chong.py
adapter/retrievers/quan_he_giua_vo_va_chong/quyen_nghia_vu_vo_chong.py
adapter/retrievers/quan_he_hon_nhan_co_yeu_to_nuoc_ngoai.py
adapter/retrievers/quy_dinh_chung_khai_niem_phap_ly.py
adapter/retrievers/quyen_nghia_vu_cha_me_con.py
adapter/retrievers/tai_san_rieng_cua_con.py
adapter/retrievers/vi_pham/xu_phat_vi_pham.py
adapter/retrievers/xac_dinh_cha_me_con.py
```

**Kiểm tra:** `rg "from application" adapter/retrievers/ --type py` phải trả về 0 kết quả.

### P1.3 — Gom đăng ký retriever vào 1 list

**Lý do:** [`presentation/main.py`](presentation/main.py) dòng 33–82 import thủ công 20+ retriever từ `adapter/retrievers/*`. Đây là skip tầng. Giải pháp: dùng [`application/retriever_catalog.py`](application/retriever_catalog.py) như tầng trung gian — đăng ký retriever ở đó, presentation chỉ import 1 list.

**Việc cụ thể:**
1. Đọc [`application/retriever_catalog.py`](application/retriever_catalog.py): xem cấu trúc `RETRIEVER_SPECS`/`RetrieverSpec` hiện tại có chứa đủ `(name, callable_fn, description_dict)` không. Nếu thiếu trường callable_fn thì bổ sung.
2. Nếu `RETRIEVER_SPECS` chưa import sẵn các retriever từ `adapter/retrievers/*`, bổ sung import (đây là việc đúng tầng vì `application` được phép import `adapter`).
3. Trong [`presentation/main.py`](presentation/main.py):
   - Xóa toàn bộ 20+ dòng `from adapter.retrievers.* import ...` (dòng 33–82).
   - Giữ lại `from adapter.config import chat_stream`, `from adapter.graph_viz import collect_viz_links`, `from adapter import data_layer` (3 cái này KHÔNG xóa vì là utility adapter, không phải retriever).
   - Thêm: `from application.retriever_catalog import RETRIEVER_SPECS` (hoặc tên list tương đương).
   - Sửa nơi đăng ký tool (tìm chỗ build `tools` dict cho Chainlit/Router) để duyệt qua `RETRIEVER_SPECS` thay vì 20 dòng thủ công.

**Lưu ý:** Việc này có thể ảnh hưởng đến cách Router gọi retriever. Phải kiểm tra `application/router.py` xem nó dùng `RETRIEVER_SPECS` hay nhận tools từ presentation. Nếu router tự lấy từ catalog thì việc trên đơn giản là cleanup presentation. Nếu router nhận từ presentation thì cần cẩn thận giữ format.

**Kiểm tra cuối:**
- `rg "from adapter.retrievers" presentation/ --type py` phải trả về 0 kết quả.
- Sơ đồ phụ thuộc cuối cùng: `presentation → application`, `presentation → adapter` (chỉ còn 3 import utility: `config`, `graph_viz`, `data_layer`), `presentation → utils`, `application → adapter`, `application → utils`, `adapter → utils`. Không còn skip tầng cho retriever, không còn back-dep.

### P1.4 — Cleanup

1. Xác nhận xóa hẳn `utils/general.py` (đã làm ở P1.1).
2. Chạy `rg "utils\.general|adapter\.retrievers" --type py` ngoài thư mục `adapter/retrievers/` và `application/` — không được có kết quả ở `presentation/` cho retriever.
3. Format lại các file đã sửa theo style sẵn có.

### P1.5 — Verify

1. `pytest -q` — phải pass (đặc biệt các test trong `tests/test_router_conversation.py`, `tests/test_legal_context.py`, `tests/test_conversation_context.py`).
2. Sinh viên smoke test thủ công: chạy Chainlit, hỏi 1–2 câu pháp lý có và không có retriever; xác nhận Router chọn đúng tool, Retriever trả context, Response LLM stream câu trả lời.
3. Optional: chạy `scripts/test_context_dedupe.py` để kiểm tra encode/decode codec không bị gãy sau khi tách module.

---

## 🛑 ĐIỂM DỪNG BẮT BUỘC

Pha 1 dừng tại đây. Composer 2.5 KHÔNG được tự động chuyển sang Pha 2. Sinh viên sẽ:

1. Review diff code, đảm bảo không có thay đổi ngoài 3 mục P1.1–P1.3.
2. Chạy test suite + smoke test Chainlit.
3. Commit changes (nếu muốn) với message dạng `refactor: align utils/adapter/application layering for thesis §4.2`.
4. Mở session mới với Opus 4.7 để bắt đầu Pha 2.

---

## PHA 2 — Tài liệu + hình vẽ (Opus 4.7)

**Mục tiêu pha 2:** Vẽ lại 2 sơ đồ gói (server + client), viết lại §4.2 trong LaTeX cho khớp code đã refactor.

**Tiền điều kiện:** Pha 1 đã merge, test pass, sinh viên xác nhận.

### P2.0 — Xác nhận lại với sinh viên

Hỏi 2 việc còn lỏng:
1. **Client diagram layout** (câu trả lời cũ là "Other" chưa rõ): tách `4.2.1 Thiết kế gói phía server` + `4.2.2 Thiết kế gói phía client` (subsection), hay gộp 1 §4.2 với 2 hình inline?
2. **Drawio style cho client diagram:** dùng phong cách phân màu (xanh/vàng/trắng) như Hình 4.2 mẫu sinh viên gửi, hay phong cách đơn sắc như `Kiến trúc tổng quan.drawio`?

### P2.1 — Tạo `Hinhve/Sơ đồ gói server.drawio`

**Yêu cầu thiết kế:**
- 4 gói xếp tầng dọc: `presentation` (trên cùng), `application`, `adapter` (theo thứ tự), `utils` (gói shared, đặt dưới hoặc tách riêng bên cạnh).
- Mỗi gói là UML package symbol (rectangle có "tab" nhỏ trên góc trái).
- Mũi tên:
  - **Dashed open arrow** (UML dependency `<<import>>` / `<<use>>`): `presentation → application`, `application → adapter`.
  - **Dotted line + open arrow**: `presentation → utils`, `application → utils`, `adapter → utils` (utils là gói shared cross-layer).
  - **Có thể bổ sung dashed arrow nhỏ** `presentation → adapter` kèm chú thích "adapter.config, adapter.graph_viz, adapter.data_layer (bootstrap)" — vì sau refactor vẫn còn 3 import utility cấp app.
- Legend nhỏ ở góc dưới: phân biệt 2 loại mũi tên.
- Phong cách: giống `Kiến trúc tổng quan.drawio` (font 19, dashed border cho khung gói lớn, rounded rectangle cho package).
- Kích thước: width ~700px (để xuất PNG vừa `\includegraphics[width=0.72\textwidth]`).

**Trách nhiệm từng gói (để gắn vào package node hoặc làm chú thích bên cạnh):**

| Gói | Module chính | Trách nhiệm |
|---|---|---|
| `presentation` | `main.py`, `guest_auth.py`, `projects_api.py`, `viz_routes.py`, `compare_actions.py` | Entry Chainlit (`on_chat_start`, `on_message`, `on_chat_resume`, `oauth_callback`), REST endpoint cho project/viz/guest, action so sánh. |
| `application` | `router.py`, `router_tool_registry.py`, `retriever_catalog.py`, `retriever_policy.py`, `conversation_context.py`, `legal_context.py`, `warning_payload.py`, `vi_phrase_match.py`, `comparison/*` | Router Agent điều phối retriever, bộ nhớ hội thoại + cache reuse, hợp nhất context pháp lý, build cảnh báo legal warning, baseline so sánh. |
| `adapter` | `config.py`, `comparison_llm.py`, `data_layer.py`, `init_db.py`, `projects.py`, `graph_viz.py`, `viz_store.py`, `guest.py`, `text2cypher.py`, `direct_tools.py`, `retrievers/*`, `cypher_templates/*` | Kết nối LLM (OpenAI/Gemini), Neo4j retriever theo template Cypher, lưu trữ phiên Postgres (Chainlit Data Layer), trực quan KG, helper guest, Chainlit direct tool. |
| `utils` | `utils.py`, `legal_context_codec.py` | Chuẩn hóa context cho LLM (`chuan_hoa_Context_cho_LLM`), parse/format ngày sự kiện, dedupe provision, codec `LEGAL_CONTEXT_BUNDLE_V1`. |

### P2.2 — Tạo `Hinhve/Sơ đồ gói client.drawio`

**Nội dung 9 gói chính + phân màu:**

| Gói | Mô tả ngắn | Màu | Nhãn legend |
|---|---|---|---|
| `pages` | `Home`, `Login`, `AuthCallback`, `Page`, `Thread`, `Element`, `Env` | 🟡 Vàng | Kế thừa, tái cấu trúc (thêm guest route guard ở `Page.tsx`, `Thread.tsx`) |
| `components` | `chat`, `header`, `Elements`, `ChatSettings`, `Tasklist`, `share`, `ui` | 🟡 Vàng | Kế thừa (chỉnh `header/UserNav.tsx` ẩn nav cho guest) |
| `components/LeftSidebar` | Sidebar lịch sử + quản lý project | 🟢 Xanh | Thêm mới |
| `state` | Recoil/Jotai atoms (sessions, threads, settings) | ⬜ Trắng | Kế thừa nguyên |
| `api` | REST + WebSocket client; thêm Projects API | 🟡 Vàng | Kế thừa, tái cấu trúc (`api/index.ts`) |
| `contexts`, `hooks` | React context + custom hooks | ⬜ Trắng | Kế thừa nguyên |
| `lib` | `auth.ts` (`canManageConversations`), formatters | 🟡 Vàng | Kế thừa, tái cấu trúc |
| `i18n` | Đa ngôn ngữ | ⬜ Trắng | Kế thừa nguyên |
| `types` | TS types; thêm `projects.ts` | 🟡 Vàng | Kế thừa, tái cấu trúc |

Bootstrap: `AppWrapper.tsx` (🟡 — guest auth bootstrap), `App.tsx`, `router.tsx`, `main.tsx` — có thể gộp thành 1 node "bootstrap" ngoài khung `src`.

**Phụ thuộc tóm tắt (chuẩn React SPA):**
- `pages → components, state, contexts, hooks, api, lib, i18n, types`
- `components → state, hooks, lib, i18n, types`
- `api → types, lib`
- `hooks → state, api`
- `state`, `types`, `i18n` ở tầng dưới cùng

**Style:** dùng UML package symbol giống Hình 4.2 mẫu; legend 3 ô vuông màu xanh/vàng/trắng ở dưới với chú thích.

**Kích thước:** width ~900px (để vừa `\includegraphics[width=\textwidth]`).

### P2.3 — Export PNG

Sinh viên tự thực hiện (Opus chỉ tạo `.drawio`, không thể export PNG trực tiếp):
1. Mở `Hinhve/Sơ đồ gói server.drawio` bằng draw.io desktop hoặc app.diagrams.net.
2. File → Export as → PNG → ghi đè `Hinhve/Sơ đồ gói.png` (resolution 200 DPI, transparent off).
3. Tương tự cho `Hinhve/Sơ đồ gói client.drawio` → `Hinhve/Sơ đồ gói client.png`.

### P2.4 — Viết lại §4.2 trong LaTeX

**Khung subsection mới** (thay thế dòng 21–35 hiện tại):

```latex
\subsection{Thiết kế tổng quan}
\label{subsection:4.2}

\subsubsection{Thiết kế gói phía server}
Phía server được tổ chức thành bốn gói (package) Python xếp theo kiến trúc phân
tầng (layered architecture), thể hiện ở Hình \ref{fig:Fig1}. Mỗi gói tương ứng
với một thư mục Python độc lập, có vai trò rõ ràng và tuân thủ nguyên tắc gói
tầng dưới không phụ thuộc gói tầng trên, không phụ thuộc bỏ qua tầng.

\begin{figure}[H]
    \centering
    \includegraphics[width=0.72\textwidth]{Hinhve/Sơ đồ gói.png}
    \caption{Biểu đồ phụ thuộc gói phía server}
    \label{fig:Fig1}
\end{figure}

\textbf{(i) Gói \texttt{presentation}} là tầng giao tiếp với người dùng và hạ
tầng Chainlit. Gói này chứa các module xử lý sự kiện hội thoại
(\texttt{main.py}), xác thực OAuth và phiên guest (\texttt{guest\_auth.py}),
REST API quản lý dự án (\texttt{projects\_api.py}) và trang trực quan đồ thị
tri thức (\texttt{viz\_routes.py}), cũng như callback so sánh đáp án
(\texttt{compare\_actions.py}).

\textbf{(ii) Gói \texttt{application}} đảm nhiệm logic nghiệp vụ và điều phối
Agentic Workflow. Các thành phần chính gồm Router Agent
(\texttt{router.py}, \texttt{router\_tool\_registry.py},
\texttt{retriever\_catalog.py}, \texttt{retriever\_policy.py}), bộ nhớ hội thoại
và cơ chế cache reuse retriever (\texttt{conversation\_context.py}), hợp nhất
và dedupe căn cứ pháp lý theo bundle (\texttt{legal\_context.py},
\texttt{warning\_payload.py}), khớp cụm từ tiếng Việt
(\texttt{vi\_phrase\_match.py}) và pipeline so sánh đáp án
(\texttt{comparison/}).

\textbf{(iii) Gói \texttt{adapter}} chịu trách nhiệm tích hợp với các hệ thống
ngoài: API LLM (\texttt{config.py}, \texttt{comparison\_llm.py}), cơ sở dữ liệu
đồ thị Neo4j thông qua các retriever theo dạng câu hỏi pháp lý
(\texttt{retrievers/}) và bộ template Cypher tương ứng
(\texttt{cypher\_templates/}), cơ sở dữ liệu PostgreSQL lưu phiên hội thoại
(\texttt{data\_layer.py}, \texttt{init\_db.py}, \texttt{projects.py}), trực quan
đồ thị tri thức (\texttt{graph\_viz.py}, \texttt{viz\_store.py}), nhận diện
người dùng guest (\texttt{guest.py}), text-to-Cypher dự phòng
(\texttt{text2cypher.py}) và các direct tool của Chainlit
(\texttt{direct\_tools.py}).

\textbf{(iv) Gói \texttt{utils}} là gói dùng chung cho toàn hệ thống, cung cấp
hàm chuẩn hóa context pháp lý cho LLM
(\texttt{utils.chuan\_hoa\_Context\_cho\_LLM}), tiện ích xử lý chuỗi và thời
gian, cùng codec mã hóa/giải mã định dạng \texttt{LEGAL\_CONTEXT\_BUNDLE\_V1}
dùng chung giữa tầng \texttt{adapter} và \texttt{application}
(\texttt{legal\_context\_codec.py}).

Quan hệ phụ thuộc giữa các gói được thể hiện trong sơ đồ gồm: phụ thuộc trực
tiếp (mũi tên nét đứt) \texttt{presentation} $\to$ \texttt{application} $\to$
\texttt{adapter}, và phụ thuộc tiện ích (mũi tên chấm) từ cả ba gói trên đến
\texttt{utils}. Cách tổ chức này tách biệt rõ ràng giao diện, nghiệp vụ và
tích hợp ngoài, tạo điều kiện thay thế độc lập từng tầng — chẳng hạn đổi
nhà cung cấp LLM hoặc cơ sở dữ liệu — mà không ảnh hưởng đến tầng nghiệp vụ.

\subsubsection{Thiết kế gói phía client}
\label{subsubsection:4.2.2}
Phía client được xây dựng trên nền frontend của Chainlit phiên bản 2.11.1,
được fork và tùy biến phục vụ cho hệ thống. Hình \ref{fig:Fig1_client} mô tả
biểu đồ gói tổng quan phía client cùng phân loại gói được thêm mới, kế thừa
tái cấu trúc và kế thừa nguyên gốc từ thư viện.

\begin{figure}[H]
    \centering
    \includegraphics[width=\textwidth]{Hinhve/Sơ đồ gói client.png}
    \caption{Biểu đồ phụ thuộc gói phía client}
    \label{fig:Fig1_client}
\end{figure}

% Mô tả ngắn từng nhóm gói (Opus điền theo bảng P2.2 ở trên)
```

Lưu ý khi viết:
- Tránh lỗi cũ: dùng "chứa" thay "chức", dùng "adapter" số ít thay "adapters".
- Mỗi gói đề cập đúng tên module chính (không bịa).
- Không dùng từ "v.v." mơ hồ — liệt kê chính xác.
- Không gọi `LegalContextBundle` là retriever — nó là *cấu trúc dữ liệu* trong codec.

### P2.5 — Build và kiểm tra

1. `powershell -File scripts/build-thesis.ps1`.
2. Mở PDF, kiểm tra:
   - Hình `fig:Fig1` xuất hiện đúng vị trí, label resolve.
   - Hình `fig:Fig1_client` xuất hiện đúng vị trí, label resolve.
   - Không lỗi LaTeX overfull/missing reference.
   - Phong cách caption + đánh số khớp các hình khác trong chương 4.

---

## Tóm tắt cho người đọc nhanh

| Pha | Agent | Việc | Output |
|---|---|---|---|
| 1 | Composer 2.5 | Refactor `utils/general.py` → `adapter/direct_tools.py`, tách codec ra `utils/legal_context_codec.py`, gom retriever vào `RETRIEVER_SPECS` | Code khớp 4 gói layered, test pass |
| — | Sinh viên | Review + test thủ công Chainlit | Xác nhận không gãy luồng |
| 2 | Opus 4.7 | Vẽ 2 drawio (server + client), viết lại §4.2 LaTeX | 2 PNG + LaTeX subsection cập nhật |

---

## Tham chiếu cho Opus 4.7 ở Pha 2

Trước khi bắt đầu Pha 2, Opus đọc:
1. File này (kế hoạch + spec đầy đủ).
2. `thesis-context/ch05-code-map.md`, `thesis-context/chat-flow.md`.
3. `ĐATN_.../Chuong/4_Ket_qua_thuc_nghiem.tex` để xem context trước/sau §4.2.
4. `ĐATN_.../Hinhve/Kiến trúc tổng quan.drawio` để học phong cách vẽ.
5. Diff Pha 1 (qua `git log -p`) để xác nhận tên file/module mới.

Không cần đọc thêm code chi tiết — đã có mô tả đầy đủ trong file này.
