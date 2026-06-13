# Chương 5 — Code Map

File đồ án: `ĐATN_20225919_Lê_Thái_Sơn_Chatbot_tư_vấn_luật_hôn_nhân_gia_đình/Chuong/5_Giai_phap_dong_gop.tex`

## §5.2 Legal reasoning (`section:5.2`)

### `subsection:5.2.1` — Dẫn dắt bài toán

- Mô tả khái niệm; ít code trực tiếp.
- Tham chiếu kiến trúc: `thesis-context/architecture.md`

### `subsection:5.2.2` — KG + Cypher templates

#### Subsubsection — Mối quan hệ văn bản QPPL

- Bảng nhãn nút: label `table: Bảng nhãn nút KG`, `tab:kg_van_ban_properties`, `tab:kg_luat_component_properties`
- Code schema: `kg-schema.md`
- **Lưu ý đồng bộ:** code dùng `DUOC_SUA_DOI_BOI` (không phải `SUA_DOI_BOI`)

#### Subsubsection — Hiệu lực + phân loại (`table:algo_temporal`)

| Đồ án | Code |
|---|---|
| Algorithm 2 giai đoạn | `adapter/cypher_templates/*/_common.py` + `utils/utils.py` |
| Truy vết thay thế | `THAY_THE_BOI*0..` / `*1..` trong `_common.py` |
| Sửa đổi / hướng dẫn | `DUOC_SUA_DOI_BOI`, `HUONG_DAN_BOI` |
| Chuẩn hóa LLM | `chuan_hoa_Context_cho_LLM` in `utils/utils.py` |
| Snippet shared | `adapter/retrievers/_context_tho_common.py` |
| Test | `scripts/test_tham_chieu_ancestor.py` |

#### Subsubsection — Schema theo dạng câu hỏi (che_do_tai_san)

- Bảng intent/nodes: `tab:intent_che_do_tai_san`, `tab:nodes_che_do_tai_san`, `tab:relationship_che_do_tai_san`
- Code:
  - `adapter/cypher_templates/tai_san/_common.py` (`TOPIC_LABEL`, `EXPAND_AND_TIMEFILTER_CYPHER`)
  - `adapter/retrievers/quan_he_giua_vo_va_chong/che_do_tai_san_cua_vo_chong.py`
  - Registry: `adapter/cypher_templates/tai_san/__init__.py`

## §Template phan_loai_tai_san (trong cùng file, ~dòng 345+)

| Đồ án | Code |
|---|---|
| `alg:phan-loai-seed` pseudocode | Templates trong `adapter/cypher_templates/tai_san/*.py` |
| Params bảng | `term_mapping.py`, từng template module |

## §Benchmark (`subsection:benchmark`)

| Đồ án | Code |
|---|---|
| Thu thập dữ liệu | `benchmark_dataset/crawl.py` |
| Schema JSON | `benchmark_dataset/benchmark_grouped/*.json` |
| Scoring | `benchmark_dataset/scripts/` (e.g. `score_router_agent.py`) |
| Kết quả | `subsection:5.1.3` — đối chiếu metric thực tế từ script output |

## Router (nếu mở rộng mô tả từ Chương 4/5)

- `application/router.py` — `route_question`, `tool_picker_prompt`
- `application/retriever_catalog.py` — `RETRIEVER_SPECS`
- `application/retriever_policy.py` — policy bổ sung
- Registry UI: `presentation/main.py`

## Retriever không dùng template registry (Cypher inline V2)

- `adapter/retrievers/quy_dinh_chung_khai_niem_phap_ly.py`
- `adapter/retrievers/ket_hon/dieu_kien_ket_hon.py`
- Pattern tương tự `_context_tho_common.py` cho THAY_THE / SUA_DOI

## Files KHÔNG dùng

- `adapter/obsolete_retrievers/**`
