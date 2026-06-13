# Prompt mẫu — Cursor Agent & Codex

## Cursor Agent

### Session khởi động (Chương 5)

```
@thesis-context/AGENT_WORKFLOW.md @thesis-context/ch05-code-map.md @Chuong/5_Giai_phap_dong_gop.tex
Đồng bộ mục được chỉ định với code thực tế. Chỉ sửa .tex; dùng lstinputlisting khi trích code.
```

### Kiểm tra không sửa file

```
@thesis-context/ch05-code-map.md @thesis-context/legal-reasoning-flow.md
So sánh algorithm env (label table:algo_temporal) với utils/utils.py và adapter/cypher_templates/chia_tai_san_sau_ly_hon/_common.py.
Liệt kê từng bước: khớp / lệch / thiếu. Không sửa file.
```

### Session theo subsection

Xem bảng prompt chi tiết trong [SYNC_SESSIONS.md](SYNC_SESSIONS.md).

---

## Codex (VS Code)

Codex tự load `AGENTS.md`. Prompt chỉ cần nhiệm vụ cụ thể.

### Session viết/sửa đồ án

```
Đọc thesis-context/AGENT_WORKFLOW.md và thesis-context/ch05-code-map.md trước khi làm việc.

Nhiệm vụ: [MÔ TẢ SUBSECTION + label LaTeX]

Ràng buộc:
- Chỉ sửa file .tex trong thư mục DATN
- Dùng \lstinputlisting cho code mẫu (≤30 dòng)
- Không bịa tên relationship Neo4j
- Output: checklist khớp/không khớp
```

### Ví dụ — hiệu lực văn bản

```
Đọc thesis-context/AGENT_WORKFLOW.md và thesis-context/ch05-code-map.md.

Nhiệm vụ: Đồng bộ subsection "Cơ chế kiểm tra tình trạng hiệu lực"
(label table:algo_temporal) trong Chuong/5_Giai_phap_dong_gop.tex với:
- adapter/cypher_templates/chia_tai_san_sau_ly_hon/_common.py
- utils/utils.py (chuan_hoa_Context_cho_LLM)

Chỉ sửa .tex. Output checklist khớp/không khớp từng bước thuật toán.
```

### Kiểm tra không sửa

```
So sánh algorithm env (label table:algo_temporal) với implementation trong utils/utils.py.
Chỉ liệt kê: khớp / lệch / thiếu. Không sửa file.
```

### Verify Codex đọc instructions (một lần sau setup)

```
Liệt kê quy tắc từ AGENTS.md và nêu 3 mục đầu tiên trong thesis-context/ch05-code-map.md.
```
