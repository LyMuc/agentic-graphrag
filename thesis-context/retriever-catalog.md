# Retriever Catalog

Map tool name (Router) → file Python. Phần bảng dưới **tự sinh** từ code khi chạy `scripts/sync-thesis-context.ps1`.

<!-- BEGIN AUTO-GENERATED:sync_thesis_context.py -->
_Cập nhật lúc 2026-06-17 14:54 UTC_

| Tool | topic_label | domain_group | File retriever | Templates |
|---|---|---|---|---|
| `cap_duong` | `cap_duong` | `cap_duong` | `adapter/retrievers/cap_duong.py` | `adapter/cypher_templates/cap_duong/` |
| `cha_me_con_sau_ly_hon` | `cha_me_con_sau_ly_hon` | `ly_hon` | `adapter/retrievers/ly_hon/cha_me_con_sau_ly_hon.py` | `adapter/cypher_templates/cha_me_con_sau_ly_hon/` |
| `che_do_tai_san_cua_vo_chong` | `che_do_tai_san_cua_vo_chong` | `tai_san` | `adapter/retrievers/quan_he_giua_vo_va_chong/che_do_tai_san_cua_vo_chong.py` | `adapter/cypher_templates/tai_san/` |
| `chia_tai_san_sau_ly_hon` | `chia_tai_san_sau_ly_hon` | `ly_hon` | `adapter/retrievers/ly_hon/chia_tai_san_sau_ly_hon.py` | `adapter/cypher_templates/chia_tai_san_sau_ly_hon/` |
| `chung_song_nhu_vo_chong` | `chung_song_nhu_vo_chong` | `ket_hon` | `adapter/retrievers/ket_hon/chung_song_nhu_vo_chong.py` | `adapter/cypher_templates/chung_song_nhu_vo_chong/` |
| `dai_dien_trach_nhiem_vo_chong` | `dai_dien_trach_nhiem_vo_chong` | `vo_chong` | `adapter/retrievers/quan_he_giua_vo_va_chong/dai_dien_trach_nhiem_vo_chong.py` | `adapter/cypher_templates/dai_dien_trach_nhiem_vo_chong/` |
| `dang_ky_ket_hon` | `dang_ky_ket_hon` | `ket_hon` | `adapter/retrievers/ket_hon/dang_ky_ket_hon.py` | `adapter/cypher_templates/dang_ky_ket_hon/` |
| `dieu_kien_ket_hon` | `dieu_kien_ket_hon` | `ket_hon` | `adapter/retrievers/ket_hon/dieu_kien_ket_hon.py` | `adapter/cypher_templates/dieu_kien_ket_hon/` |
| `han_che_quyen_cha_me_con_chua_thanh_nien` | `han_che_quyen_cha_me_con_chua_thanh_nien` | `cha_me_con` | `adapter/retrievers/han_che_quyen_cha_me_con_chua_thanh_nien.py` | `adapter/cypher_templates/han_che_quyen_cha_me_con_chua_thanh_nien/` |
| `hon_nhan_cham_dut_do_vo_chong_chet` | `hon_nhan_cham_dut_do_vo_chong_chet` | `hon_nhan` | `adapter/retrievers/hon_nhan_cham_dut_do_vo_chong_chet.py` | `adapter/cypher_templates/hon_nhan_cham_dut_do_vo_chong_chet/` |
| `ket_hon_trai_phap_luat` | `ket_hon_trai_phap_luat` | `ket_hon` | `adapter/retrievers/ket_hon/ket_hon_trai_phap_luat.py` | `adapter/cypher_templates/ket_hon_trai_phap_luat/` |
| `quan_he_giua_cac_thanh_vien_khac_trong_gia_dinh` | `quan_he_giua_cac_thanh_vien_khac_trong_gia_dinh` | `family_members` | `adapter/retrievers/quan_he_giua_cac_thanh_vien_khac_trong_gia_dinh.py` | `adapter/cypher_templates/quan_he_giua_cac_thanh_vien_khac_trong_gia_dinh/` |
| `quan_he_hon_nhan_co_yeu_to_nuoc_ngoai` | `quan_he_hon_nhan_co_yeu_to_nuoc_ngoai` | `foreign` | `adapter/retrievers/quan_he_hon_nhan_co_yeu_to_nuoc_ngoai.py` | `adapter/cypher_templates/quan_he_hon_nhan_co_yeu_to_nuoc_ngoai/` |
| `quy_dinh_chung_khai_niem_phap_ly` | `quy_dinh_chung_khai_niem_phap_ly` | `general` | `adapter/retrievers/quy_dinh_chung_khai_niem_phap_ly.py` | `adapter/cypher_templates/quy_dinh_chung_khai_niem_phap_ly/` |
| `quy_dinh_chung_ly_hon` | `quy_dinh_chung_ly_hon` | `ly_hon` | `adapter/retrievers/ly_hon/quy_dinh_chung_ly_hon.py` | `adapter/cypher_templates/quy_dinh_chung_ly_hon/` |
| `quyen_nghia_vu_cha_me_con` | `quyen_nghia_vu_cha_me_con` | `cha_me_con` | `adapter/retrievers/quyen_nghia_vu_cha_me_con.py` | `adapter/cypher_templates/quyen_nghia_vu_cha_me_con/` |
| `quyen_nghia_vu_vo_chong` | `quyen_nghia_vu_vo_chong` | `vo_chong` | `adapter/retrievers/quan_he_giua_vo_va_chong/quyen_nghia_vu_vo_chong.py` | `adapter/cypher_templates/quyen_nghia_vu_vo_chong/` |
| `tai_san_rieng_cua_con` | `tai_san_rieng_cua_con` | `cha_me_con` | `adapter/retrievers/tai_san_rieng_cua_con.py` | `adapter/cypher_templates/tai_san_rieng_cua_con/` |
| `xac_dinh_cha_me_con` | `xac_dinh_cha_me_con` | `cha_me_con` | `adapter/retrievers/xac_dinh_cha_me_con.py` | `adapter/cypher_templates/xac_dinh_cha_me_con/` |
| `xu_phat_vi_pham` | `xu_phat_vi_pham` | `vi_pham` | `adapter/retrievers/vi_pham/xu_phat_vi_pham.py` | `adapter/cypher_templates/xu_phat_vi_pham/` |

**Direct tools (không qua retriever):** `respond`, `text2cypher`

Tổng retriever trong catalog: **20** (alias index: 21).

Nguồn code: `application/retriever_catalog.py`, `application/router_tool_registry.py`, `presentation/main.py`.
<!-- END AUTO-GENERATED:sync_thesis_context.py -->
