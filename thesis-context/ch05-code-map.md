# Chương 5 — Code Map

File đồ án: `ĐATN_20225919_Lê_Thái_Sơn_Chatbot_tư_vấn_luật_hôn_nhân_gia_đình/Chuong/5_Giai_phap_dong_gop.tex`

**Quy mô hiện tại (2026-06):** **20 retriever** + 2 direct tool (`respond`, `text2cypher`); **20** `TemplateRegistry` trong `registry_index.py`. Bảng đầy đủ: `retriever-catalog.md`, `cypher-template-index.md` (chạy `sync-thesis-context.ps1` trước khi đối chiếu).

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

## Router (Chương 4/5 — mô tả hệ retriever)

- `application/router.py` — `route_question`, `tool_picker_prompt`
- `application/retriever_catalog.py` — `RETRIEVER_SPECS` (**20** tool)
- `application/retriever_policy.py` — policy bổ sung
- `application/router_tool_registry.py` — schema tool cho LLM
- Registry UI: `presentation/main.py`

Danh sách tool ↔ file ↔ template: **`retriever-catalog.md`** (auto).

## Retriever đang sử dụng + Cypher templates

Toàn bộ retriever đang sử dụng nằm trong `adapter/retrievers/`. Mọi retriever chính đều có thư mục `adapter/cypher_templates/<topic>/` và đăng ký trong `ALL_TEMPLATE_REGISTRIES` — **trừ mapping đặc biệt**:

| Tool | Thư mục template | Ghi chú |
|---|---|---|
| `che_do_tai_san_cua_vo_chong` | `adapter/cypher_templates/tai_san/` | Registry key `tai_san`, không trùng tên tool |

Các domain mới (2026): `xac_dinh_cha_me_con`, `tai_san_rieng_cua_con`, `ket_hon_trai_phap_luat`, `quyen_nghia_vu_vo_chong`, `dai_dien_trach_nhiem_vo_chong`, `quyen_nghia_vu_cha_me_con`, `quan_he_hon_nhan_co_yeu_to_nuoc_ngoai`, `quan_he_giua_cac_thanh_vien_khac_trong_gia_dinh`, `xu_phat_vi_pham`, `quy_dinh_chung_khai_niem_phap_ly` — xem số template trong `cypher-template-index.md`.

Snippet hiệu lực / tham chiếu chung vẫn dùng `adapter/retrievers/_context_tho_common.py` trong `_common.py` từng domain.

## Files KHÔNG dùng

- `adapter/obsolete_retrievers/**`
