# Agentic GraphRAG Chatbot Luật

Hệ thống chatbot vấn đáp pháp luật Việt Nam, ứng dụng kiến trúc **Agentic GraphRAG**: LLM định tuyến câu hỏi tới các bộ truy xuất chuyên biệt, mỗi bộ sinh truy vấn **Cypher** trên **Neo4j** để lấy căn cứ pháp lý (Điều, Khoản, Điểm, mối quan hệ tham chiếu, hiệu lực văn bản), rồi LLM tổng hợp câu trả lời có trích dẫn.

Trọng tâm hiện tại: **Luật Hôn nhân và Gia đình** và các văn bản liên quan; có thêm retriever **xử phạt vi phạm hành chính** (Nghị định, Bộ luật Hình sự khi cần).

---

## Tính năng nổi bật

- **Agentic Router**: LLM phân tích câu hỏi (kể cả nhiều ý trong một câu), chọn **một hoặc nhiều** retriever phù hợp và chạy **song song**.
- **GraphRAG theo domain**: Mỗi retriever có schema Cypher và danh sách Điều luật gợi ý riêng; hỗ trợ lọc theo **thời điểm sự kiện** (áp dụng luật tại thời điểm quá khứ nếu người dùng nêu).
- **Text2Cypher dự phòng**: Retriever tổng quát khi không khớp domain cụ thể.
- **Tổng hợp đáp án có kiểm soát**: Prompt phản hồi quy định cách trích dẫn Điều/Khoản/Điểm, thứ bậc văn bản, hiệu lực, văn bản sửa đổi và cảnh báo đa cấp pháp lý.
- **Giao diện Chainlit**: Streaming câu trả lời, hiển thị từng bước (Router, Retriever, tổng hợp).
- **Visualize đồ thị**: Sau mỗi câu trả lời từ retriever hỗ trợ trực quan hóa, link mở trang web riêng (Neo4j Browser-style) hiển thị node/quan hệ từ `Context_Tho` + lớp ngữ nghĩa.
- **Lưu hội thoại**: PostgreSQL qua Chainlit Data Layer (thread, step, resume chat).
- **Projects**: Nhóm nhiều thread theo từng người dùng ngay trong sidebar Chainlit.
- **Đánh giá benchmark**: Bộ câu hỏi chuẩn, script điền đáp án chatbot và tính metric trích dẫn pháp lý.

---

## Kiến trúc

```text
Người dùng (Chainlit UI)
        │
        ▼
presentation/main.py          ← Đăng ký tools, prompt, lifecycle
        │
        ├── application/router.py      ← Chọn tool (ROUTER_LLM)
        ├── application/query_updater.py  ← (tùy chọn) làm rõ câu hỏi theo lịch sử
        │
        ▼
adapter/retrievers/*          ← Trích xuất Điều luật (RETRIEVER_LLM) → Cypher → Neo4j
utils/general.py              ← text2cypher, answer_given
        │
        ▼
adapter/config.py             ← Neo4j driver, LLM (Vercel AI Gateway)
        │
        ▼
LLM tổng hợp (RESPONSE_LLM)   ← Streaming câu trả lời cuối
```

| Lớp | Thư mục | Vai trò |
|-----|---------|---------|
| **Presentation** | `presentation/` | Entry Chainlit, registry tools, OAuth, session |
| **Application** | `application/` | Router, query updater |
| **Adapter** | `adapter/` | Cấu hình Neo4j/LLM/DB, retriever theo chủ đề |
| **Domain** | `domain/` | Schema DB (nếu dùng) |
| **Utils** | `utils/` | Chuẩn hóa kết quả Cypher, text2cypher, tiện ích chung |

---

## Retriever (tools) hiện có

| Tool | Chủ đề |
|------|--------|
| `quy_dinh_chung_khai_niem_phap_ly` | Quy định chung, khái niệm pháp lý |
| `dieu_kien_ket_hon` | Điều kiện kết hôn |
| `dang_ky_ket_hon` | Đăng ký kết hôn |
| `ket_hon_trai_phap_luat` | Kết hôn trái pháp luật |
| `chung_song_nhu_vo_chong` | Chung sống như vợ chồng |
| `hon_nhan_cham_dut_do_vo_chong_chet` | Hôn nhân chấm dứt do vợ/chồng chết |
| `cap_duong` | Nghĩa vụ cấp dưỡng |
| `quan_he_hon_nhan_co_yeu_to_nuoc_ngoai` | Quan hệ hôn nhân có yếu tố nước ngoài |
| `tai_san_rieng_cua_con` | Tài sản riêng của con |
| `quy_dinh_chung_ly_hon` | Quy định chung ly hôn |
| `chia_tai_san_sau_ly_hon` | Chia tài sản sau ly hôn |
| `cha_me_con_sau_ly_hon` | Cha mẹ, con sau ly hôn |
| `quyen_nghia_vu_vo_chong` | Quyền, nghĩa vụ vợ chồng |
| `dai_dien_trach_nhiem_vo_chong` | Đại diện, trách nhiệm vợ chồng |
| `che_do_tai_san_cua_vo_chong` | Chế độ tài sản vợ chồng |
| `xu_phat_vi_pham` | Xử phạt vi phạm hành chính |
| `text2cypher` | Truy vấn đồ thị tổng quát |
| `respond` | Trả lời không cần truy xuất (ít dùng) |

Thêm retriever mới: tạo module trong `adapter/retrievers/`, khai báo `description` + hàm async, rồi đăng ký trong `presentation/main.py` (`tools` dict).

---

## Yêu cầu hệ thống

- **Python** 3.9+ (khuyến nghị 3.11+)
- **Docker & Docker Compose** — PostgreSQL (và tùy chọn pgAdmin) cho Chainlit
- **Neo4j** — instance đã import dữ liệu pháp luật (`bolt://localhost:7687` mặc định)
- **Vercel AI Gateway API Key** — gọi LLM qua endpoint OpenAI-compatible

---

## Cài đặt & chạy

### 1. PostgreSQL (Chainlit)

Từ thư mục gốc dự án:

```bash
docker compose up -d
```

- PostgreSQL: `localhost:5432`, DB `chainlit_db`, user/pass `postgres` / `123456` (theo `docker-compose.yml`)
- pgAdmin (tùy chọn): http://localhost:5050

### 2. Neo4j

Đảm bảo Neo4j đang chạy và graph đã có node/quan hệ pháp luật (Điều luật, văn bản, hiệu lực, tham chiếu, …). Cấu hình qua biến môi trường (xem bước 3).

### 3. Môi trường Python

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
```

### 4. Biến môi trường

Copy `.env.example` thành `.env` và điền giá trị:

```ini
# Bắt buộc — Vercel AI Gateway
VERCEL_AI_GATEWAY_API_KEY=your-vercel-ai-gateway-key
AI_GATEWAY_BASE_URL=https://ai-gateway.vercel.sh/v1

# Model (tùy chọn, mặc định trong adapter/config.py)
RESPONSE_LLM=openai/gpt-4.1
ROUTER_LLM=openai/gpt-4o
RETRIEVER_LLM=openai/o3

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-neo4j-password
NEO4J_DATABASE=neo4j

# PostgreSQL — Chainlit Data Layer
DATABASE_URL=postgresql+asyncpg://postgres:123456@localhost:5432/chainlit_db
CHAINLIT_AUTH_SECRET=change-me-to-a-long-random-string

# OAuth (tùy chọn — bật trong .chainlit/config.toml)
OAUTH_GOOGLE_CLIENT_ID=
OAUTH_GOOGLE_CLIENT_SECRET=
OAUTH_GITHUB_CLIENT_ID=
OAUTH_GITHUB_CLIENT_SECRET=
```

Trong `adapter/config.py` có sẵn khối cấu hình **Gemini API trực tiếp** (đang comment) nếu muốn chuyển provider sau này.

### 5. Khởi chạy ứng dụng

**Terminal 1 — Chatbot Chainlit:**

```bash
chainlit run presentation/main.py -w
```

### Build frontend Chainlit tùy biến

Frontend được giữ theo baseline Chainlit `2.11.1` và mở rộng sidebar Projects
cùng chế độ chat guest. Bundle production được commit tại
`public/chainlit-build`.

```powershell
cd frontend
npx.cmd pnpm@9.15.9 install --frozen-lockfile
npx.cmd pnpm@9.15.9 type-check
npx.cmd pnpm@9.15.9 test
npx.cmd pnpm@9.15.9 build
```

- `-w`: auto-reload khi sửa code
- UI chat: **http://localhost:8000**
- Link visualize (chế độ chuyên gia): **http://localhost:8000/viz/{viz_id}** — cùng process Chainlit
- Snapshot JSON lưu tại `data/viz_snapshots/` (TTL 7 ngày)
- Lần chạy đầu, Chainlit tạo schema PostgreSQL tự động nếu `DATABASE_URL` hợp lệ

**Viz server riêng (tùy chọn — dev hoặc tách tải materialize):**

```bash
uvicorn presentation.viz_server:app --host 0.0.0.0 --port 8501
```

Khi dùng port riêng, set `.env`: `VIZ_BASE_URL=http://localhost:8501`

**Guest và OAuth:** Người dùng chưa đăng nhập vẫn chat được nhưng hội thoại
không được lưu và không có lịch sử/Projects. Nút **Login** mở trang OAuth mặc
định của Chainlit; sau khi đăng nhập, lịch sử và Projects được bật cho tài khoản.

---

## Cấu trúc thư mục (phần chính)

```text
├── presentation/main.py       # Entry Chainlit
├── application/
│   ├── router.py              # Định tuyến tool
│   └── query_updater.py         # Làm rõ câu hỏi theo lịch sử
├── adapter/
│   ├── config.py                # Neo4j, LLM, DATABASE_URL
│   ├── data_layer.py            # Chainlit ↔ PostgreSQL
│   └── retrievers/              # Retriever theo chủ đề
├── utils/                       # Chuẩn hóa context, text2cypher
├── benchmark_dataset/           # QA benchmark & script đánh giá
│   ├── benchmark/               # Bộ câu hỏi gốc theo chủ đề
│   ├── test_versions/           # Phiên bản test (JSON)
│   ├── scripts/                 # fill_test_answers, gen_test_results, …
│   └── result/                  # Tổng hợp kết quả chạy test
├── data/                        # Nguồn văn bản, script crawl (tham khảo)
├── docker-compose.yml           # PostgreSQL + pgAdmin
├── requirements.txt
└── .env.example
```

---

## Benchmark & đánh giá

Pipeline gợi ý (cần `.env` và Neo4j giống lúc chạy chat):

```bash
# Điền chatbot_answer + context cho file test
python -m benchmark_dataset.scripts.fill_test_answers benchmark_dataset/test_versions/cap_duong/test_v1_1705_cap_duong.json

# Gộp metric theo chủ đề / toàn bộ
python -m benchmark_dataset.scripts.gen_test_results

# Chấm metric trích dẫn pháp lý (tùy file)
python -m benchmark_dataset.scripts.score_legal_metrics path/to/test.json
```

Các script khác: `build_test_version.py`, `build_grouped_benchmark.py`, `normalize_benchmark.py`, `merge_test_versions.py` — xem docstring trong từng file.

---

## Luồng xử lý một câu hỏi (tóm tắt)

1. Người dùng gửi tin nhắn trên Chainlit.
2. **Router** (`ROUTER_LLM`) chọn một hoặc nhiều tool; mỗi tool chạy trong `cl.Step` riêng.
3. Retriever: LLM structured output chọn `dieu_luat_ids` (+ thời điểm nếu có) → thực thi Cypher trên Neo4j → `chuan_hoa_ket_qua_retriever`.
4. Gộp `contexts` từ các retriever → **Response LLM** stream câu trả lời theo `main_prompt` (trích dẫn, hiệu lực, thứ bậc văn bản).
5. Lưu lịch sử session; thread/steps persist qua PostgreSQL.

---

## Ghi chú vận hành

- Thiếu `VERCEL_AI_GATEWAY_API_KEY` → lỗi khi khởi tạo LLM.
- Thiếu `DATABASE_URL` → chat vẫn chạy nhưng **không** lưu thread lâu dài (cảnh báo trong `adapter/data_layer.py`).
- `query_update` theo lịch sử hiện **tắt** trong `main.py` (`updated_question = input_text`); có thể bật lại bằng cách gọi `query_update`.
- Dữ liệu thô văn bản pháp luật nằm ở `data/`; đồ thị Neo4j cần được chuẩn bị/import riêng trước khi chạy chatbot.
