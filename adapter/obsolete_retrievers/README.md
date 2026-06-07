# Obsolete retrievers

Các file trong thư mục này là implementation cũ (trích xuất Điều luật + Cypher domain),
đã được thay bằng retriever semantic-graph trong `adapter/retrievers/`.

**Không import** các module này trong runtime, router, hay benchmark.

| File | Thay thế bởi |
|------|----------------|
| `ly_hon/chia_tai_san_sau_ly_hon.py` | `adapter/retrievers/ly_hon/chia_tai_san_sau_ly_hon.py` |
| `quan_he_giua_vo_va_chong/che_do_tai_san_cua_vo_chong.py` | `adapter/retrievers/quan_he_giua_vo_va_chong/che_do_tai_san_cua_vo_chong.py` |
