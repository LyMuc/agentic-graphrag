import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import chainlit as cl
# Gọi data_layer để Chainlit thiết lập PostgreSQL connection lúc khởi động
from adapter import data_layer 
from chainlit import data as cl_data
from adapter.config import chat_stream
from application.query_updater import query_update
from application.router import route_question
from adapter.graph_viz import collect_viz_links

from adapter.retrievers.cap_duong import cap_duong, cap_duong_description
from adapter.retrievers.hon_nhan_cham_dut_do_vo_chong_chet import (
    hon_nhan_cham_dut_do_vo_chong_chet,
    hon_nhan_cham_dut_do_vo_chong_chet_description,
)
from adapter.retrievers.ket_hon.chung_song_nhu_vo_chong import (
    chung_song_nhu_vo_chong,
    chung_song_nhu_vo_chong_description,
)
from adapter.retrievers.ket_hon.dang_ky_ket_hon import dang_ky_ket_hon, dang_ky_ket_hon_description
from adapter.retrievers.ket_hon.dieu_kien_ket_hon import dieu_kien_ket_hon, dieu_kien_ket_hon_description
from adapter.retrievers.ket_hon.ket_hon_trai_phap_luat import ket_hon_trai_phap_luat, ket_hon_trai_phap_luat_description
from adapter.retrievers.ly_hon.cha_me_con_sau_ly_hon import cha_me_con_sau_ly_hon, cha_me_con_sau_ly_hon_description
from adapter.retrievers.ly_hon.chia_tai_san_sau_ly_hon import chia_tai_san_sau_ly_hon, chia_tai_san_sau_ly_hon_description
from adapter.retrievers.ly_hon.chia_tai_san_sau_ly_hon_v3 import (
    chia_tai_san_sau_ly_hon_v3,
    chia_tai_san_sau_ly_hon_v3_description,
)
from adapter.retrievers.ly_hon.quy_dinh_chung_ly_hon import quy_dinh_chung_ly_hon, quy_dinh_chung_ly_hon_description
from adapter.retrievers.quan_he_giua_vo_va_chong.che_do_tai_san_cua_vo_chong import (
    che_do_tai_san_cua_vo_chong,
    che_do_tai_san_cua_vo_chong_description,
)
from adapter.retrievers.quan_he_giua_vo_va_chong.dai_dien_trach_nhiem_vo_chong import (
    dai_dien_trach_nhiem_vo_chong,
    dai_dien_trach_nhiem_vo_chong_description,
)
from adapter.retrievers.quan_he_giua_vo_va_chong.quyen_nghia_vu_vo_chong import (
    quyen_nghia_vu_vo_chong,
    quyen_nghia_vu_vo_chong_description,
)
from adapter.retrievers.quan_he_hon_nhan_co_yeu_to_nuoc_ngoai import (
    quan_he_hon_nhan_co_yeu_to_nuoc_ngoai,
    quan_he_hon_nhan_co_yeu_to_nuoc_ngoai_description,
)
from adapter.retrievers.quy_dinh_chung_khai_niem_phap_ly import (
    quy_dinh_chung_khai_niem_phap_ly,
    quy_dinh_chung_khai_niem_phap_ly_description,
)
# from adapter.retrievers.quan_he_giua_vo_va_chong.che_do_tai_san_cua_vo_chong_v2 import (
#     che_do_tai_san_cua_vo_chong_v2,
#     che_do_tai_san_cua_vo_chong_v2_description,
# )
from adapter.retrievers.quan_he_giua_vo_va_chong.che_do_tai_san_cua_vo_chong_v3 import (
    che_do_tai_san_cua_vo_chong_v3,
    che_do_tai_san_cua_vo_chong_v3_description,
)
from adapter.retrievers.han_che_quyen_cha_me_con_chua_thanh_nien import (
    han_che_quyen_cha_me_con_chua_thanh_nien,
    han_che_quyen_cha_me_con_chua_thanh_nien_description,
)
from adapter.retrievers.quan_he_giua_cac_thanh_vien_khac_trong_gia_dinh import (
    quan_he_giua_cac_thanh_vien_khac_trong_gia_dinh,
    quan_he_giua_cac_thanh_vien_khac_trong_gia_dinh_description,
)
from adapter.retrievers.quyen_nghia_vu_cha_me_con import (
    quyen_nghia_vu_cha_me_con,
    quyen_nghia_vu_cha_me_con_description,
)
from adapter.retrievers.tai_san_rieng_cua_con import tai_san_rieng_cua_con, tai_san_rieng_cua_con_description
from adapter.retrievers.xac_dinh_cha_me_con import xac_dinh_cha_me_con, xac_dinh_cha_me_con_description
from adapter.retrievers.vi_pham.xu_phat_vi_pham import xu_phat_vi_pham, xu_phat_vi_pham_description
from utils.general import text2cypher, text2cypher_description, answer_given, answer_given_description
from chainlit.types import ThreadDict
from typing import Dict, Optional

tools = {
    "quy_dinh_chung_khai_niem_phap_ly": {
        "description": quy_dinh_chung_khai_niem_phap_ly_description,
        "function": quy_dinh_chung_khai_niem_phap_ly
    },
    "dieu_kien_ket_hon": {
        "description": dieu_kien_ket_hon_description,
        "function": dieu_kien_ket_hon
    },
    "dang_ky_ket_hon": {
        "description": dang_ky_ket_hon_description,
        "function": dang_ky_ket_hon
    },
    "ket_hon_trai_phap_luat": {
        "description": ket_hon_trai_phap_luat_description,
        "function": ket_hon_trai_phap_luat
    },
    "chung_song_nhu_vo_chong": {
        "description": chung_song_nhu_vo_chong_description,
        "function": chung_song_nhu_vo_chong
    },
    "hon_nhan_cham_dut_do_vo_chong_chet": {
        "description": hon_nhan_cham_dut_do_vo_chong_chet_description,
        "function": hon_nhan_cham_dut_do_vo_chong_chet
    },
    "cap_duong": {
        "description": cap_duong_description,
        "function": cap_duong
    },
    "quan_he_hon_nhan_co_yeu_to_nuoc_ngoai": {
        "description": quan_he_hon_nhan_co_yeu_to_nuoc_ngoai_description,
        "function": quan_he_hon_nhan_co_yeu_to_nuoc_ngoai
    },
    "tai_san_rieng_cua_con": {
        "description": tai_san_rieng_cua_con_description,
        "function": tai_san_rieng_cua_con
    },
    "quyen_nghia_vu_cha_me_con": {
        "description": quyen_nghia_vu_cha_me_con_description,
        "function": quyen_nghia_vu_cha_me_con
    },
    "han_che_quyen_cha_me_con_chua_thanh_nien": {
        "description": han_che_quyen_cha_me_con_chua_thanh_nien_description,
        "function": han_che_quyen_cha_me_con_chua_thanh_nien
    },
    "xac_dinh_cha_me_con": {
        "description": xac_dinh_cha_me_con_description,
        "function": xac_dinh_cha_me_con
    },
    "quan_he_giua_cac_thanh_vien_khac_trong_gia_dinh": {
        "description": quan_he_giua_cac_thanh_vien_khac_trong_gia_dinh_description,
        "function": quan_he_giua_cac_thanh_vien_khac_trong_gia_dinh
    },
    "quy_dinh_chung_ly_hon": {
        "description": quy_dinh_chung_ly_hon_description,
        "function": quy_dinh_chung_ly_hon
    },
    "chia_tai_san_sau_ly_hon": {
        "description": chia_tai_san_sau_ly_hon_description,
        "function": chia_tai_san_sau_ly_hon
    },
    # "chia_tai_san_sau_ly_hon_v3": {
    #     "description": chia_tai_san_sau_ly_hon_v3_description,
    #     "function": chia_tai_san_sau_ly_hon_v3
    # },
    "cha_me_con_sau_ly_hon": {
        "description": cha_me_con_sau_ly_hon_description,
        "function": cha_me_con_sau_ly_hon
    },
    "quyen_nghia_vu_vo_chong": {
        "description": quyen_nghia_vu_vo_chong_description,
        "function": quyen_nghia_vu_vo_chong
    },
    "dai_dien_trach_nhiem_vo_chong": {
        "description": dai_dien_trach_nhiem_vo_chong_description,
        "function": dai_dien_trach_nhiem_vo_chong
    },
    "che_do_tai_san_cua_vo_chong": {
        "description": che_do_tai_san_cua_vo_chong_description,
        "function": che_do_tai_san_cua_vo_chong
    },
    # "che_do_tai_san_cua_vo_chong_v2": {
    #     "description": che_do_tai_san_cua_vo_chong_v2_description,
    #     "function": che_do_tai_san_cua_vo_chong_v2
    # },
    # "che_do_tai_san_cua_vo_chong_v3": {
    #     "description": che_do_tai_san_cua_vo_chong_v3_description,
    #     "function": che_do_tai_san_cua_vo_chong_v3
    # },
    "xu_phat_vi_pham": {
        "description": xu_phat_vi_pham_description,
        "function": xu_phat_vi_pham
    },
    "text2cypher": {
        "description": text2cypher_description,
        "function": text2cypher
    },
    "respond": {
        "description": answer_given_description,
        "function": answer_given
    }
}

main_prompt = """
Bạn là một Luật sư cấp cao và chuyên gia pháp chế tại Việt Nam.
Hãy giải đáp tình huống pháp lý của người dùng dựa TRỌN VẸN vào phần [CĂN CỨ PHÁP LÝ TỪ HỆ THỐNG] bên dưới.

NGUYÊN TẮC CHẮT LỌC THÔNG TIN (TUYỆT ĐỐI TUÂN THỦ):
Hệ thống có thể cung cấp nhiều Khoản/Điểm liên quan đến cùng một Điều luật. Tuy nhiên, BẠN CHỈ ĐƯỢC PHÉP CHỌN LỌC VÀ TRÌNH BÀY những Khoản, Điểm TRỰC TIẾP trả lời cho câu hỏi của người dùng. 
Tuyệt đối KHÔNG liệt kê, KHÔNG nhắc đến các Khoản/Điểm không liên quan hoặc không phục vụ cho việc trả lời cho câu hỏi.
LƯU Ý QUAN TRỌNG: Việc lọc Khoản/Điểm KHÔNG có nghĩa là được bỏ qua dòng tiêu đề "Điều X. [Tên điều]". Khi trích dẫn nội dung, BẮT BUỘC phải giữ cấu trúc phân cấp đầy đủ: Điều → (Khoản nếu có) → (Điểm nếu có).

QUY TẮC BẮT BUỘC VỀ HIỆU LỰC VĂN BẢN (TUYỆT ĐỐI TUÂN THỦ):
Trong phần "THÔNG TIN HIỆU LỰC VĂN BẢN" của dữ liệu, hệ thống cung cấp ngày có hiệu lực và ngày hết hiệu lực (nếu có) của từng văn bản. BẠN BẮT BUỘC phải tuân thủ:

1. LUÔN GHI NGÀY HIỆU LỰC: Khi dẫn chiếu bất kỳ văn bản pháp luật nào trong câu mở đầu, BẮT BUỘC phải ghi kèm "có hiệu lực từ ngày DD-MM-YYYY".
   Ví dụ: "Căn cứ theo quy định tại Khoản 1, 2 Điều 43 và Khoản 1 Điều 44 Luật Hôn nhân và Gia đình 2014 có hiệu lực từ ngày 01-01-2015"

2. CẢNH BÁO VĂN BẢN HẾT HIỆU LỰC: Nếu văn bản có thông tin "HẾT HIỆU LỰC vào ngày...", BẮT BUỘC phải thêm cảnh báo trong ngoặc đơn ngay sau ngày hiệu lực.
   Ví dụ: "Căn cứ vào Nghị định 82/2020/NĐ-CP có hiệu lực từ ngày 01-09-2020 (Cảnh báo: Văn bản hết hiệu lực vào ngày 18-05-2026)"

3. FORMAT NGÀY THÁNG: Tất cả ngày tháng trong câu trả lời PHẢI theo format DD-MM-YYYY (ngày-tháng-năm), phù hợp với bối cảnh Việt Nam. TUYỆT ĐỐI KHÔNG dùng format YYYY-MM-DD.

4. KHI CÓ NHIỀU VĂN BẢN: Mỗi văn bản được dẫn chiếu đều phải có thông tin hiệu lực riêng.
   Ví dụ: "Căn cứ theo Luật Hôn nhân và Gia đình 2014 có hiệu lực từ ngày 01-01-2015, được hướng dẫn chi tiết tại Nghị định 126/2014/NĐ-CP có hiệu lực từ ngày 01-01-2015"

5. VĂN BẢN SỬA ĐỔI, BỔ SUNG: Khi dẫn chiếu văn bản sửa đổi (ví dụ: "được sửa đổi, bổ sung bởi..." hoặc văn bản hướng dẫn bị sửa), BẮT BUỘC phải ghi kèm hiệu lực của chính văn bản sửa đổi đó (và cảnh báo hết hiệu lực nếu có).
   Ví dụ: "Căn cứ theo quy định tại Điều 37 Luật Hôn nhân và Gia đình 2014 có hiệu lực từ ngày 01-01-2015, được sửa đổi, bổ sung bởi Điều 4 Nghị định 120/2025/NĐ-CP có hiệu lực từ ngày 01-07-2025"
   Ví dụ hướng dẫn bị sửa: "Căn cứ theo Khoản 3 Điều 30 Nghị định 126/2014/NĐ-CP có hiệu lực từ ngày 01-01-2015, được sửa đổi, bổ sung bởi Khoản 9 Điều 2 Nghị định 07/2025/NĐ-CP có hiệu lực từ ngày 15-03-2025"

NHIỆM VỤ ĐẶC BIỆT KHI XÂY DỰNG LẬP LUẬN:
Hãy kiểm tra phần "THÔNG TIN CẢNH BÁO" trong dữ liệu cung cấp và BẮT BUỘC áp dụng các quy tắc hành văn sau:

1. NẾU CÓ CẢNH BÁO "CÓ_NHIỀU_CẤP_BẬC_PHÁP_LÝ":
Bạn BẮT BUỘC phải đọc kỹ nội dung phần [CĂN CỨ PHÁP LÝ TỪ HỆ THỐNG] để chọn ĐÚNG 1 trong 2 kịch bản dẫn dắt sau:

- KỊCH BẢN 1 (CHỈ DÙNG CHO CÂU HỎI VỀ MỨC PHẠT/TỘI PHẠM): CHỈ KÍCH HOẠT kịch bản này NẾU trong nội dung căn cứ pháp lý CÓ chứa các từ khóa về chế tài như: "phạt tiền", "phạt cảnh cáo", "phạt tù".

  TRÌNH TỰ LẬP LUẬN BẮT BUỘC (TUYỆT ĐỐI KHÔNG ĐẢO NGƯỢC):
  Bước 1 - KHẲNG ĐỊNH HÀNH VI BỊ CẤM (NẾU CÓ TRONG CONTEXT):
  Nếu trong [CĂN CỨ PHÁP LÝ TỪ HỆ THỐNG] có các Điều/Khoản/Điểm quy định hành vi bị cấm, điều kiện cấm, hoặc hành vi trái pháp luật liên quan trực tiếp đến câu hỏi, BẮT BUỘC phải trích dẫn các điều luật đó TRƯỚC TIÊN, khẳng định rõ hành vi trong câu hỏi là hành vi bị cấm/không được phép, rồi mới chuyển sang phần xử phạt.
  Ví dụ: "Căn cứ theo quy định tại [Điểm/Khoản/Điều] thuộc Luật Hôn nhân và Gia đình 2014 có hiệu lực từ ngày 01-01-2015, hành vi [nêu tên hành vi trong câu hỏi] là hành vi bị cấm. Cụ thể như sau:
  Điều X. [Tên điều]
  [Khoản/Điểm liên quan]
  Do đó, hành vi [nêu tên hành vi trong câu hỏi] là vi phạm pháp luật."

  Bước 2 - TRÌNH BÀY CHẾ TÀI XỬ PHẠT:
  Sau khi đã khẳng định hành vi bị cấm (nếu có căn cứ trong Context), mới trình bày các quy định về xử phạt. Bạn PHẢI kiểm tra kỹ các cấp bậc văn bản để chọn ĐÚNG 1 TRONG 2 cách mở đầu phần chế tài sau:

   + Trường hợp 1a (Trong Context CHỈ CÓ Nghị định phạt tiền/cảnh cáo, KHÔNG CÓ Luật hình sự):
     -> Mở đầu phần chế tài bằng: "Đối với hành vi vi phạm này, người thực hiện hành vi sẽ bị xử phạt vi phạm hành chính. Cụ thể như sau:"

   + Trường hợp 1b (Trong Context CÓ CẢ Nghị định phạt hành chính VÀ Bộ luật Hình sự phạt tù):
     -> Mở đầu phần chế tài bằng: "Đối với hành vi vi phạm này, tùy theo tính chất và mức độ vi phạm, người thực hiện hành vi có thể bị xử phạt vi phạm hành chính hoặc bị truy cứu trách nhiệm hình sự. Cụ thể như sau:"
     -> TRÌNH TỰ SẮP XẾP BẮT BUỘC: Bạn PHẢI trình bày quy định Xử phạt hành chính (Nghị định - Cấp bậc 2) TRƯỚC TIÊN. Sau đó mới dẫn chiếu đến quy định Hình sự (Bộ luật Hình sự - Cấp bậc 1) như một hậu quả đối với trường hợp vi phạm nghiêm trọng.

- KỊCH BẢN 2 (TƯ VẤN DÂN SỰ, THỦ TỤC, CÁCH TÒA ÁN GIẢI QUYẾT):
  TUYỆT ĐỐI KHÔNG mở đầu bằng câu "Theo nguyên tắc thứ bậc hiệu lực pháp lý, chúng ta sẽ căn cứ chính vào..." hay các câu tương tự. Hãy đi thẳng vào trình bày các căn cứ pháp lý.

  TRÌNH TỰ SẮP XẾP BẮT BUỘC (TUYỆT ĐỐI KHÔNG LÀM TRÁI): Luật (Cấp bậc 1) → Nghị định (Cấp bậc 2) → Thông tư/Thông tư liên tịch (Cấp bậc 3).

  QUY TẮC NÊU MỐI QUAN HỆ GIỮA CÁC VĂN BẢN (BẮT BUỘC):
  Khi trình bày từng văn bản, BẮT BUỘC phải nêu rõ mối quan hệ pháp lý giữa các văn bản: văn bản nào hướng dẫn văn bản nào, văn bản nào sửa đổi/bổ sung văn bản nào. Không được trích dẫn rời rạc mà không làm rõ liên kết.

  CẤU TRÚC TRÌNH BÀY BẮT BUỘC:
  + Với Luật (văn bản gốc): "Căn cứ theo quy định tại [Điểm/Khoản/Điều] [Tên Luật] có hiệu lực từ ngày DD-MM-YYYY, [vấn đề] được quy định như sau:" → trích dẫn nội dung.
  + Với Nghị định/Thông tư hướng dẫn: "Căn cứ theo [Điểm/Khoản/Điều] [Tên Nghị định/Thông tư] có hiệu lực từ ngày DD-MM-YYYY, hướng dẫn [Điểu/Khoản] [Tên Luật] quy định như sau:" → trích dẫn nội dung.
  + Với văn bản sửa đổi/bổ sung: "Căn cứ theo [Điểu/Khoản] [Tên văn bản mới] có hiệu lực từ ngày DD-MM-YYYY, sửa đổi, bổ sung [Điều/Khoản] [Tên văn bản gốc] quy định như sau:" → trích dẫn nội dung.

  VÍ DỤ MẪU:
  "Căn cứ theo quy định tại Khoản 1 Điều 43 Luật Hôn nhân và Gia đình 2014 có hiệu lực từ ngày 01-01-2015, tài sản riêng của vợ, chồng được quy định như sau:
  Điều 43. Tài sản riêng của vợ, chồng
  1. [Nội dung Khoản 1 liên quan]

  Căn cứ theo Điều 5 Nghị định 126/2014/NĐ-CP có hiệu lực từ ngày 01-01-2015, hướng dẫn Điều 43 Luật Hôn nhân và Gia đình 2014 quy định như sau:
  Điều 5. [Tên điều]
  [Nội dung Khoản/Điểm liên quan]"

2. NẾU CÓ CẢNH BÁO "CÓ_VĂN_BẢN_SỬA_ĐỔI":
Bạn phải nhìn kỹ vào nội dung căn cứ xem văn bản nào đang bị sửa đổi để áp dụng ĐÚNG 1 TRONG 2 cấu trúc sau:
- Trường hợp Luật bị sửa đổi bởi Luật: Bắt buộc dùng cấu trúc: "Căn cứ theo quy định tại [Tên Luật gốc], được sửa đổi, bổ sung bởi [Tên Luật mới]..."
- Trường hợp Luật KHÔNG bị sửa, mà chỉ có Nghị định/Thông tư hướng dẫn bị sửa: TUYỆT ĐỐI KHÔNG ĐƯỢC nói Luật chính bị sửa. Bắt buộc dùng cấu trúc ngoặc đơn: "Căn cứ theo quy định tại [Tên Luật Chính], được hướng dẫn chi tiết tại [Tên Nghị định/Thông tư gốc] (đã được sửa đổi, bổ sung bởi [Tên Nghị định/Thông tư mới])..."
- TRONG PHẦN TRÍCH DẪN CHI TIẾT ĐIỀU LUẬT: 
  Bạn BẮT BUỘC phải chèn cụm từ chú thích "(Được sửa đổi, bổ sung bởi...)" vào ngay sau chữ "Điều", hoặc ngay đầu "Khoản/Điểm" bị sửa đổi. (Xem cấu trúc bắt buộc tại Quy tắc 5).
* LƯU Ý TỐI QUAN TRỌNG: Luôn lấy nội dung của văn bản MỚI NHẤT (văn bản đi sửa đổi) để tư vấn, tuyệt đối không dùng nội dung của bản gốc đã bị sửa.

3. NẾU CÓ CẢNH BÁO LỊCH SỬ (ÁP DỤNG LUẬT CŨ):
Bắt buộc phải mở đầu phần tư vấn bằng câu: "Mặc dù quy định mới nhất hiện hành là [Tên luật mới], nhưng do sự kiện pháp lý của bạn xảy ra tại thời điểm [Thời gian quá khứ], nên theo nguyên tắc áp dụng pháp luật, chúng ta phải áp dụng căn cứ pháp lý tại thời điểm đó là [Tên Luật Cũ]. Cụ thể như sau..."

4. TRƯỜNG HỢP CƠ BẢN (Chỉ có 1 căn cứ, hoặc không có cảnh báo nào):
Hãy trả lời trực tiếp, đi thẳng vào vấn đề. TRONG CÂU DẪN DẮT, BẠN PHẢI NÊU CHÍNH XÁC ĐẾN TẬN ĐIỂM, KHOẢN (nếu có) được dùng để trả lời, TUYỆT ĐỐI KHÔNG chỉ nêu chung chung tên Điều.

5. CÁCH TRÌNH BÀY TRÍCH DẪN (TUYỆT ĐỐI TUÂN THỦ FORMAT):
BẮT BUỘC trình bày dưới dạng cấu trúc pháp luật gốc.
- KHÔNG chú thích nguồn ở cuối câu (VD: không dùng "(Căn cứ: Điều X...)").
- MỖI Khoản (1, 2...) và Điểm (a, b...) PHẢI XUỐNG DÒNG riêng biệt.
- NGOẠI LỆ: Khi có cảnh báo "CÓ_NHIỀU_CẤP_BẬC_PHÁP_LÝ" (Kịch bản 2), BẮT BUỘC lặp lại "Căn cứ theo..." cho TỪNG văn bản ở mỗi cấp bậc (Luật, Nghị định, Thông tư) và nêu rõ mối quan hệ giữa chúng như quy định tại Kịch bản 2.

QUY TẮC BẮT BUỘC VỀ DÒNG TIÊU ĐỀ ĐIỀU (TUYỆT ĐỐI KHÔNG BỎ QUA):
Sau câu dẫn dắt "Cụ thể như sau:" (hoặc tương đương), PHẦN TRÍCH DẪN NỘI DUNG BẮT BUỘC phải bắt đầu bằng dòng "Điều X. [Tên điều]" lấy từ nội dung trong Context, rồi mới đến Khoản/Điểm liên quan.
TUYỆT ĐỐI KHÔNG được nhảy thẳng vào "a)", "b)", "1.", "2." mà thiếu dòng "Điều X. [Tên điều]" phía trên.
Nếu chỉ trích dẫn 1 Điểm/Khoản con, vẫn PHẢI ghi đủ: (1) dòng Điều, (2) dòng Khoản cha (nếu Điểm nằm trong Khoản), (3) dòng Điểm/Khoản được hỏi.

[VÍ DỤ SAI - TUYỆT ĐỐI KHÔNG LÀM]:
Căn cứ theo quy định tại Điểm a Khoản 1 Điều 8 Luật Hôn nhân và Gia đình 2014..., điều kiện kết hôn được quy định như sau:
a) Nam từ đủ 20 tuổi trở lên, nữ từ đủ 18 tuổi trở lên;

[VÍ DỤ ĐÚNG - BẮT BUỘC LÀM THEO]:
Căn cứ theo quy định tại Điểm a Khoản 1 Điều 8 Luật Hôn nhân và Gia đình 2014..., điều kiện kết hôn được quy định như sau:
Điều 8. Điều kiện kết hôn
1. Nam từ đủ 20 tuổi trở lên, nữ từ đủ 18 tuổi trở lên, được kết hôn trong các trường hợp sau đây:
a) Nam từ đủ 20 tuổi trở lên, nữ từ đủ 18 tuổi trở lên;

[VÍ DỤ ĐÚNG - TRÍCH DẪN NGHỊ ĐỊNH XỬ PHẠT]:
Căn cứ theo Khoản 1 Điều 58 Nghị định 82/2020/NĐ-CP..., hành vi tảo hôn bị xử phạt như sau:
Điều 58. Tảo hôn
1. Phạt tiền từ 1.000.000 đồng đến 3.000.000 đồng đối với hành vi tổ chức lấy vợ, lấy chồng cho người chưa đủ tuổi kết hôn.

CẤU TRÚC MỞ ĐẦU CHUNG:
Căn cứ theo quy định tại [Điểm, Khoản, Điều, Văn bản gốc], vấn đề này được quy định như sau:

QUY TẮC CHÈN CHÚ THÍCH SỬA ĐỔI (HÃY BẮT CHƯỚC 3 VÍ DỤ SAU):
Nếu có thông tin sửa đổi, cụm từ "(Được sửa đổi, bổ sung bởi...)" BẮT BUỘC phải được đặt ngay sát cạnh cấp độ bị sửa đổi.

[Mẫu 1 - Cơ bản, không sửa đổi]:
Điều 3. Giải thích từ ngữ
18. Những người có họ trong phạm vi ba đời là...

[Mẫu 2 - Sửa TOÀN BỘ Điều]:
Điều 37. (Được sửa đổi, bổ sung bởi Điều 4 Nghị định 120/2025/NĐ-CP) Thẩm quyền đăng ký kết hôn
1. Ủy ban nhân dân cấp xã thực hiện...

[Mẫu 3 - Giữ nguyên Điều, CHỈ sửa Khoản/Điểm]:
Điều 30. Thủ tục đăng ký kết hôn
3. (Được sửa đổi, bổ sung bởi Khoản 9 Điều 2 Nghị định 07/2025/NĐ-CP) Hồ sơ nộp trực tuyến...

6. CÁCH SỬ DỤNG "CĂN CỨ THAM CHIẾU BỔ TRỢ":
Nếu có "CĂN CỨ THAM CHIẾU BỔ TRỢ" và nó THỰC SỰ LIÊN QUAN ĐẾN CÂU HỎI, hãy nối mạch văn bằng câu: "Đồng thời, dẫn chiếu đến quy định tại [Tên Điều tham chiếu], nội dung này được quy định cụ thể như sau:" và tiếp tục dùng format trích dẫn Điều luật (BẮT BUỘC có dòng "Điều X. [Tên điều]" trước Khoản/Điểm) như ở Quy tắc 5.

7. KHÔNG BỊA ĐẶT:
Nếu thông tin pháp luật không có trong phần "CĂN CỨ PHÁP LÝ TỪ HỆ THỐNG", hãy trả lời rằng "Dựa trên thông tin hiện có, tôi không tìm thấy căn cứ pháp lý phù hợp để giải đáp câu hỏi của bạn. Bạn có thể cung cấp thêm chi tiết hoặc đặt câu hỏi khác không?"

10. QUY TẮC LIÊN KẾT TRÍCH DẪN (BẮT BUỘC KHI CÓ `--- BẢNG LINK TRÍCH DẪN (TVPL) ---`):
Bảng link chỉ liệt kê cấp Điều. Khi trích dẫn trong câu dẫn dẫn hoặc bullet mâu thuẫn, BẮT BUỘC bọc phần tên điều khoản + văn bản bằng markdown link `[text](url)`.

Áp dụng cho:
- Câu dẫn dẫn: "Căn cứ theo...", "được sửa đổi, bổ sung bởi...", "dẫn chiếu đến...", "hướng dẫn..."
- Mục **CẢNH BÁO MÂU THUẪN**, dòng "Các điều khoản mâu thuẫn:" (bullet list)

KHÔNG áp dụng link cho:
- Phần trích dẫn nguyên văn ("Điều X. [Tên điều]", Khoản, Điểm) — kể cả block mâu thuẫn phía dưới
- Phần "có hiệu lực từ ngày...", cảnh báo hết hiệu lực

Quy tắc khớp URL:
- Chỉ dùng URL từ `--- BẢNG LINK TRÍCH DẪN (TVPL) ---`; TUYỆT ĐỐI KHÔNG tự bịa URL.
- Trích dẫn Điều: dùng URL của Điều đó trong bảng.
- Trích dẫn Khoản/Điểm: giữ nguyên text đầy đủ (vd. "Khoản 1 Điều 43..."), dùng URL của **Điều cha** trong bảng.
- Không có URL trong bảng → plain text như hiện tại.

[VÍ DỤ ĐÚNG — trích dẫn Điều]:
Căn cứ theo quy định tại [Điều 8 Luật Hôn nhân và Gia đình 2014](https://thuvienphapluat.vn/...?anchor=dieu_8) có hiệu lực từ ngày 01-01-2015, điều kiện kết hôn được quy định như sau:
Điều 8. Điều kiện kết hôn
1. ...

[VÍ DỤ ĐÚNG — trích dẫn Khoản, URL lấy từ Điều cha]:
Căn cứ theo quy định tại [Khoản 1 Điều 43 Luật Hôn nhân và Gia đình 2014](https://thuvienphapluat.vn/...?anchor=dieu_43) có hiệu lực từ ngày 01-01-2015...

8. CẢNH BÁO MÂU THUẪN PHÁP LÝ (BẮT BUỘC KHI CÓ CỜ "CO_MAU_THUAN"):
Nếu trong phần "THÔNG TIN CẢNH BÁO" có cờ "Mâu thuẫn: CO_MAU_THUAN", BẮT BUỘC phải thêm một phần riêng ở CUỐI câu trả lời (sau toàn bộ nội dung tư vấn chính), với tiêu đề in hoa:

**CẢNH BÁO MÂU THUẪN:**

Cấu trúc bắt buộc:
- Diễn giải mâu thuẫn: Trích dẫn lại nguyên văn nội dung từ trường "Giải thích mâu thuẫn" trong phần "THÔNG TIN MÂU THUẪN PHÁP LÝ" (tương ứng với thuộc tính noidung của quan hệ MAU_THUAN_VOI). KHÔNG được tự suy diễn hay bịa thêm.
- Các điều khoản mâu thuẫn: Liệt kê các điều khoản liên quan bằng TÊN PHÁP LÝ ĐẦY ĐỦ; nếu có `--- BẢNG LINK TRÍCH DẪN (TVPL) ---`, bọc tên điều khoản bằng markdown link (Quy tắc 10)
- Trích dẫn nội dung các điều luật còn mâu thuẫn, chồng chéo: Trình bày nội dung các điều khoản mâu thuẫn/chồng chéo theo format trích dẫn pháp luật (BẮT BUỘC có dòng "Điều X. [Tên điều]" trước Khoản/Điểm). Chỉ trích dẫn các điều khoản thuộc nhóm mâu thuẫn, chồng chéo — không lặp lại toàn bộ câu trả lời chính.

Ví dụ mẫu:
**CẢNH BÁO MÂU THUẪN:**
Quy định về độ tuổi (07 tuổi) cần lấy ý kiến của con khi cha, mẹ ly hôn chưa thật sự tương thích với Luật Nuôi con nuôi, Nghị định số 123/2015/NĐ-CP.

Các điều khoản mâu thuẫn:
- [Luật Hôn nhân và Gia đình 2014, Điều 81, Khoản 2](url_dieu_81)
- [Luật Nuôi con nuôi 2010, Điều 21, Khoản 1](url_dieu_21)
- [Nghị định số 123/2015/NĐ-CP, Điều 7, Khoản 1](url_dieu_7)

Trích dẫn nội dung các điều luật còn mâu thuẫn, chồng chéo:
Điều 21. ...
1. [Nội dung Khoản 1]

Điều 7. ...
1. [Nội dung Khoản 1]

9. VĂN BẢN SẮP CÓ HIỆU LỰC (BẮT BUỘC KHI CÓ CỜ "CÓ_VĂN_BẢN_SẮP_CÓ_HIỆU_LỰC"):
Quy tắc này CHỈ áp dụng khi người dùng KHÔNG nêu mốc thời gian cụ thể trong câu hỏi (câu hỏi áp dụng theo thời điểm hiện tại). Nếu người dùng nêu mốc thời gian (quá khứ hoặc tương lai), BỎ QUA quy tắc này và trả lời một bước theo luật tại thời điểm đó.

Khi `THÔNG TIN CẢNH BÁO` có `Sắp hiệu lực: CÓ_VĂN_BẢN_SẮP_CÓ_HIỆU_LỰC`:

1. Phần trả lời chính — chỉ dựa trên `--- CĂN CỨ CHÍNH ---`, `--- CĂN CỨ HƯỚNG DẪN ---`, `--- CĂN CỨ THAM CHIẾU BỔ TRỢ ---` (văn bản đã có hiệu lực tại thời điểm hiện tại).
2. Tuyệt đối KHÔNG dùng nội dung từ `--- VĂN BẢN ĐÃ BAN HÀNH, CHƯA CÓ HIỆU LỤC ---` làm căn cứ áp dụng hiện tại; không viết "có hiệu lực từ" cho các văn bản này — phải dùng "dự kiến/sẽ có hiệu lực từ". Riêng phần **LƯU Ý** ở cuối: được phép và BẮT BUỘC trích dẫn nguyên văn từ mục `NỘI DUNG TRÍCH DẪN CHO PHẦN LƯU Ý` (không tóm tắt, không bỏ Khoản/Điểm).
3. Phần bổ sung BẮT BUỘC ở cuối câu trả lời (sau tư vấn chính), tiêu đề:

**LƯU Ý VỀ THAY ĐỔI PHÁP LUẬT SẮP CÓ HIỆU LỰC:**

Cấu trúc bắt buộc:
- Dòng 1: tên văn bản + ngày ban hành (DD-MM-YYYY) + ngày dự kiến có hiệu lực (DD-MM-YYYY) + loại tác động + căn cứ bị ảnh hưởng (theo dòng tóm tắt quan hệ).
- Tiếp theo: trích dẫn NGUYÊN VĂN toàn bộ nội dung liên quan trong `NỘI DUNG TRÍCH DẪN CHO PHẦN LƯU Ý` (Điều, Khoản, Điểm — giữ đúng thứ tự, không rút gọn). Nếu có Điều thay thế (vd. Điều 16 Luật Hộ tịch 2026), phải trích hết các Khoản/Điểm của Điều đó có trong context.
- Không được bỏ qua ngày ban hành nếu dữ liệu có trong context.

4. Trường hợp hết hiệu lực theo lịch (loại HET_HIEU_LUC): nêu rõ căn cứ hiện hành sẽ hết hiệu lực từ ngày X (không gọi là bãi bỏ); nếu có văn bản thay thế sắp hiệu lực thì nối mạch.
5. Trường hợp bãi bỏ (loại BAI_BO, quan hệ BAI_BO_BOI): nêu rõ văn bản bãi bỏ + ngày ban hành + ngày dự kiến có hiệu lực + căn cứ bị bãi bỏ.

Ví dụ mẫu:
Hiện tại, căn cứ theo Điều 107 Luật Hôn nhân và Gia đình 2014 có hiệu lực từ 01-01-2015... [trả lời chính]

**LƯU Ý VỀ THAY ĐỔI PHÁP LUẬT SẮP CÓ HIỆU LỰC:**
Luật ... đã được ban hành ngày ..., dự kiến có hiệu lực từ ..., sẽ thay thế [căn cứ cũ]. Nội dung quy định mới:
Điều ... 
1. ...
2. ...
[a full quote from NỘI DUNG TRÍCH DẪN CHO PHẦN LƯU Ý]
"""

# =================================================================
# AUTHENTICATION HOOKS (OAUTH)
# =================================================================
@cl.oauth_callback
def oauth_callback(
    provider_id: str,
    token: str,
    raw_user_data: Dict[str, str],
    default_user: cl.User,
) -> Optional[cl.User]:
    """
    Xử lý thông tin trả về sau khi người dùng đăng nhập Google/Github thành công.
    Map vào identifier để PostgreSQL lưu trữ user mới.
    """
    identifier = raw_user_data.get("email") or raw_user_data.get("login") or str(raw_user_data.get("id"))
    name = raw_user_data.get("name") or identifier
    
    metadata = {
        "name": name,
        "avatar_url": raw_user_data.get("avatar_url") or raw_user_data.get("picture"),
        "provider": provider_id
    }
    
    return cl.User(
        identifier=identifier,
        metadata=metadata
    )

# =================================================================
# CHAT LIFECYCLE HOOKS (START & RESUME FROM SIDEBAR)
# =================================================================
@cl.on_chat_start
async def on_chat_start():
    # Reset history
    cl.user_session.set("session_history", [])
    
    # Xác định user đang login
    user = cl.user_session.get("user")
    name = user.metadata.get("name") if user and user.metadata else "bạn"
    
    await cl.Message(content=f"Chào {name}, tôi là trợ lý ảo về Luật Hôn nhân và Gia đình Việt Nam. Tôi có thể giúp gì cho bạn?").send()

@cl.on_chat_resume
async def on_chat_resume(thread: ThreadDict):
    """
    Hook này chạy khi User bấm vào một đoạn chat cũ trên Sidebar.
    Kéo các steps đã lưu từ PostgreSQL lên và ép lại thành `session_history`.
    """
    # Trên Chainlit 2.x, thread được truyền vào đã có sẵn mảng "steps" (chứa danh sách dict của các steps)
    steps = thread.get("steps", [])
    
    session_history = []
    for step in steps:
        step_type = step.get("type", "")
        # Thông thường tin nhắn chat của người dùng có type là user_message, của bot là assistant_message
        if step_type == "user_message":
             session_history.append({"role": "user", "content": step.get("output", "")})
        elif step_type == "assistant_message":
             session_history.append({"role": "assistant", "content": step.get("output", "")})
                 
    cl.user_session.set("session_history", session_history)


def _viz_footer(tool_response: list) -> str:
    base = os.environ.get("VIZ_BASE_URL", "http://localhost:8501").rstrip("/")
    links = collect_viz_links(tool_response)
    if not links:
        return ""
    parts = [
        f"[Link visualize đồ thị tri thức]({base}/viz/{viz_id})"
        for viz_id, _ in links
    ]
    return "\n\n" + "\n".join(parts)


@cl.on_message
async def main(message: cl.Message):
    input_text = message.content
    session_history = cl.user_session.get("session_history")

    async with cl.Step(name="Luồng truy xuất ngữ cảnh") as p_step:
        # 1. Cập nhật câu hỏi dựa trên lịch sử
        # async with cl.Step(name="Query Updater", type="tool") as step1:
        #     step1.input = input_text
        #     updated_question = await query_update(input_text, session_history)
        #     step1.output = updated_question

        updated_question = input_text

        # 2. Lấy dữ liệu lần 1
        async with cl.Step(name="Router Agent", type="tool") as step2:
            step2.input = f'Router Input: "{updated_question}"'
            tool_response = await route_question(updated_question, tools, session_history)
            step2.metadata = {"tool_response": tool_response}
            retriever_names = []
            # for res in tool_response:
            #     if isinstance(res, dict):
            #         retriever_names.append(
            #             f"- {len(res.get('contexts', []))} context, "
            #             f"{len(res.get('raw_ids', {}).get('can_cu_chinh', []))} căn cứ chính"
            #         )
            #     else:
            #         retriever_names.append(f"- {str(res)}")
            step2.output = "Retriever cuối cùng đã chạy xong."
        
        p_step.output = "Hoàn tất truy xuất ngữ cảnh pháp lý."

    contexts_for_llm = []
    for res in tool_response:
        if isinstance(res, dict) and "contexts" in res:
            contexts_for_llm.extend(res["contexts"])
        elif isinstance(res, list):
            contexts_for_llm.extend(str(item) for item in res if item is not None)
        else:
            contexts_for_llm.append(res)

    # Chỉ bỏ qua LLM khi tool trả thẳng 1 chuỗi (vd `respond` / answer_given).
    # Retriever trả list[str] (vd v3) sau khi extend vẫn phải qua bước tổng hợp đáp án.
    if (
        len(tool_response) == 1
        and isinstance(tool_response[0], str)
        and not any(isinstance(res, dict) and "contexts" in res for res in tool_response)
    ):
        direct_answer = tool_response[0]
        viz_extra = _viz_footer(tool_response)
        msg = cl.Message(content=direct_answer + viz_extra)
        await msg.send()
        session_history.append({"role": "user", "content": input_text})
        session_history.append({"role": "assistant", "content": direct_answer + viz_extra})
        cl.user_session.set("session_history", session_history)
        return

    contexts_text_for_llm = "\n\n".join(str(ctx) for ctx in contexts_for_llm)

    current_context = list(session_history)
    current_context.append({
        "role": "system",
        "content": f"Dữ liệu lấy được từ hệ thống cho câu hỏi '{updated_question}':\n{contexts_text_for_llm}"
    })

    # Sinh câu trả lời cuối cùng (streaming)
    llm_messages = [
        {"role": "system", "content": main_prompt},
        *current_context,
        {"role": "user", "content": f"Câu hỏi của người dùng: {input_text}"},
    ]
    msg = cl.Message(content="")
    llm_response = ""
    async with cl.Step(name="Tổng hợp đáp án", type="llm") as ans_step:
        ans_step.input = "Context:\n" + contexts_text_for_llm
        try:
            async for token in chat_stream(llm_messages):
                llm_response += token
                await msg.stream_token(token)
        except Exception:
            fallback = (
                "Xin lỗi, hệ thống gặp sự cố kết nối khi sinh câu trả lời. "
                "Vui lòng thử lại sau vài giây."
            )
            if llm_response:
                llm_response += f"\n\n{fallback}"
                await msg.stream_token(f"\n\n{fallback}")
            else:
                llm_response = fallback
                await msg.stream_token(fallback)
        ans_step.output = llm_response

    viz_extra = _viz_footer(tool_response)
    if viz_extra:
        llm_response += viz_extra
        await msg.stream_token(viz_extra)

    await msg.update()

    session_history.append({"role": "user", "content": input_text})
    session_history.append({"role": "assistant", "content": llm_response})
    cl.user_session.set("session_history", session_history)

