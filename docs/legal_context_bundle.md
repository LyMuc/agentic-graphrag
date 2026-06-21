# LegalContextBundle và loại trùng context

## Mục đích

Các template retriever đã migrate sang bundle không gửi thẳng chuỗi pháp lý đã
render. Mỗi template kiểu này trả một `LegalContextBundle` được encode trong
`contexts`. Presentation layer decode, hợp nhất và chỉ render một lần trước khi
gọi Response LLM.

Trạng thái code hiện tại là mixed-compatible: retriever import
`encode_context_record` trả `LEGAL_CONTEXT_BUNDLE_V1`, còn retriever legacy vẫn
gọi trực tiếp `chuan_hoa_Context_cho_LLM` và trả text đã render. Pipeline vẫn
giữ legacy text để không làm lỗi câu trả lời, nhưng dedupe căn cứ pháp lý chỉ
được đảm bảo cho bundle.

Luồng:

```text
Context_Tho từ Neo4j
→ build_legal_context_bundle
→ encode_legal_context_bundle
→ contexts của retriever
→ process_context_strings
→ group theo target_date
→ merge_legal_context_bundles
→ render_legal_context_bundle
→ prompt Response LLM
```

Context cũ không có prefix `LEGAL_CONTEXT_BUNDLE_V1:` được xem là legacy text.
Hệ thống giữ nguyên text đó và không cố parse bằng regex.

## Data contract

Ví dụ rút gọn:

```json
{
  "schema_version": 1,
  "target_date": "2026-06-11",
  "is_user_provided_date": false,
  "provenance": [
    {
      "retriever": "chia_tai_san_sau_ly_hon",
      "template": "nguyen_tac_chia_tai_san_ly_hon"
    }
  ],
  "provisions": [
    {
      "id": "Luat_HNGD_2014_Dieu_59_Khoan_2",
      "content": "...",
      "role": "main",
      "legal_rank": 1,
      "effective_from": "2015-01-01",
      "effective_until": null,
      "amendment_id": null,
      "amended_content": null,
      "provenance": []
    }
  ],
  "guidance_relations": [],
  "future_relations": [],
  "conflicts": [],
  "replacement_ids": [],
  "citation_links": {}
}
```

Khóa phiên bản dùng để loại trùng:

```text
provision_id + amendment_id + effective_from + effective_until
```

Ưu tiên vai trò:

```text
main > guidance > support
```

Quan hệ hướng dẫn, tương lai và mâu thuẫn được dedupe riêng. Việc nâng vai trò
của provision không xóa quan hệ của provision đó.

## Kịch bản kiểm thử

### 1. Trùng `main/main`

Input:

```text
Template A: Điều 59 Khoản 2, role=main
Template B: Điều 59 Khoản 2, role=main
```

Trạng thái merge:

```text
provision key giống nhau
→ giữ một provision
→ provenance = [Template A, Template B]
```

Output render chỉ có một lần nội dung Điều 59 Khoản 2.

### 2. Trùng `main/support`

Input:

```text
Retriever chia tài sản: Điều 59, role=main
Retriever chế độ tài sản: Điều 59, role=support
```

Kết quả:

```text
role cuối = main
section cuối = CĂN CỨ CHÍNH
provenance vẫn chứa cả hai retriever
```

Không render lại Điều 59 trong `CĂN CỨ THAM CHIẾU BỔ TRỢ`.

### 3. Trùng `guidance/support` và giữ quan hệ

Input:

```text
Bundle A:
  Nghị định X Điều 3, role=support

Bundle B:
  Nghị định X Điều 3, role=guidance
  relation: Nghị định X Điều 3 hướng dẫn Luật Y Điều 8
```

Kết quả:

```text
Nghị định X Điều 3 → role=guidance
guidance relation → vẫn tồn tại
```

Renderer đặt provision trong `CĂN CỨ HƯỚNG DẪN` và vẫn sinh dòng quan hệ hướng
dẫn.

### 4. Trùng giữa nhiều template và nhiều retriever

Input:

```text
cap_duong/template_muc_cap_duong → Điều 116
cap_duong/template_phuong_thuc → Điều 116
cha_me_con_sau_ly_hon/template_nghia_vu → Điều 116
```

Pipeline nhận ba encoded contexts, gom cùng `target_date`, merge theo provision
key và render Điều 116 một lần. Debug của từng retriever vẫn độc lập trong
Chainlit step.

### 5. Không gộp hai bản sửa đổi

Input:

```text
Bundle A:
  id=Điều 30 Khoản 3
  amendment_id=null

Bundle B:
  id=Điều 30 Khoản 3
  amendment_id=Nghị định 07/2025 Điều 2 Khoản 9
```

Hai key khác nhau nên cả hai phiên bản được giữ. Đây là hành vi bảo thủ nhằm
không làm mất thông tin sửa đổi.

### 6. Không gộp hai ngày áp dụng

Input:

```text
Bundle A: target_date=2020-01-01
Bundle B: target_date=2026-06-11
```

`process_context_strings` tạo hai temporal group. Hai bundle được render riêng,
không đưa vào cùng một phép merge.

### 7. Dedupe quan hệ và cảnh báo

Input từ hai template giống nhau:

```text
guidance relation: X hướng dẫn Y
future relation: Z thay thế Y
conflict: Y mâu thuẫn W
replacement: M
```

Kết quả:

```text
guidance relation → 1
future relation → 1, ưu tiên bản có nội dung future provision
conflict pair → 1
replacement ID → 1
```

Nội dung tương lai, ngày ban hành, ngày hiệu lực và giải thích mâu thuẫn được
giữ nguyên.

### 8. Link TVPL và ngày hiệu lực

`citation_links` được lấy khi tạo bundle và hợp nhất theo ID Điều. Renderer nhận
mapping đã lưu, vì vậy không cần tự bịa hoặc parse URL từ text.

Kiểm tra output:

```text
--- THÔNG TIN HIỆU LỰC VĂN BẢN ---
...
--- BẢNG LINK TRÍCH DẪN (TVPL) ---
...
```

### 9. Mixed template và legacy context

Input:

```text
LEGAL_CONTEXT_BUNDLE_V1:{...}
"Legacy context không parse."
```

Kết quả:

```text
bundle → merge + render
legacy string → nối nguyên văn sau phần bundle
```

Legacy context không làm pipeline lỗi. Dedupe giữa bundle và legacy text không
được cam kết cho tới khi retriever legacy được migrate.

## Quan sát debug

Trong Router/Retriever step:

- `debug` cho biết template, lý do chọn và params.
- Bundle chứa `provenance` để biết provision đến từ retriever/template nào.
- `tool_response[*].contexts` trong Router metadata chứa encoded bundle.
- Output hiển thị của retriever step đã được render, không hiển thị JSON encode.

Unit test tương ứng nằm tại `tests/test_legal_context.py`.
