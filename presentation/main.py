import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
import chainlit as cl
# Gọi data_layer để Chainlit thiết lập PostgreSQL connection lúc khởi động
from adapter import data_layer 
from chainlit import data as cl_data
from adapter.config import chat_stream
from application.query_updater import query_update
from application.router import route_question

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
from adapter.retrievers.tai_san_rieng_cua_con import tai_san_rieng_cua_con, tai_san_rieng_cua_con_description
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
    "quy_dinh_chung_ly_hon": {
        "description": quy_dinh_chung_ly_hon_description,
        "function": quy_dinh_chung_ly_hon
    },
    "chia_tai_san_sau_ly_hon": {
        "description": chia_tai_san_sau_ly_hon_description,
        "function": chia_tai_san_sau_ly_hon
    },
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

NHIỆM VỤ ĐẶC BIỆT KHI XÂY DỰNG LẬP LUẬN:
Hãy kiểm tra phần "THÔNG TIN CẢNH BÁO" trong dữ liệu cung cấp và BẮT BUỘC áp dụng các quy tắc hành văn sau:

1. NẾU CÓ CẢNH BÁO "CÓ_NHIỀU_CẤP_BẬC_PHÁP_LÝ":
Bạn BẮT BUỘC phải đọc kỹ nội dung phần [CĂN CỨ PHÁP LÝ TỪ HỆ THỐNG] để chọn ĐÚNG 1 trong 2 kịch bản dẫn dắt sau:

- KỊCH BẢN 1 (CHỈ DÙNG CHO CÂU HỎI VỀ MỨC PHẠT/TỘI PHẠM): CHỈ KÍCH HOẠT kịch bản này NẾU trong nội dung căn cứ pháp lý CÓ chứa các từ khóa về chế tài như: "phạt tiền", "phạt cảnh cáo", "phạt tù".
  Bạn PHẢI kiểm tra kỹ các cấp bậc văn bản trong [CĂN CỨ PHÁP LÝ TỪ HỆ THỐNG] để chọn ĐÚNG 1 TRONG 2 cách mở đầu sau:

   + Trường hợp 1a (Trong Context CHỈ CÓ Nghị định phạt tiền/cảnh cáo, KHÔNG CÓ Luật hình sự):
     -> Bắt buộc mở đầu bằng: "Đối với hành vi vi phạm này, người thực hiện hành vi sẽ bị xử phạt vi phạm hành chính. Cụ thể như sau:"

   + Trường hợp 1b (Trong Context CÓ CẢ Nghị định phạt hành chính VÀ Bộ luật Hình sự phạt tù):
     -> Bắt buộc mở đầu bằng: "Đối với hành vi vi phạm này, tùy theo tính chất và mức độ vi phạm, người thực hiện hành vi có thể bị xử phạt vi phạm hành chính hoặc bị truy cứu trách nhiệm hình sự. Cụ thể như sau:"
     -> TRÌNH TỰ SẮP XẾP BẮT BUỘC: Bạn PHẢI trình bày quy định Xử phạt hành chính (Nghị định - Cấp bậc 2) TRƯỚC TIÊN. Sau đó mới dẫn chiếu đến quy định Hình sự (Bộ luật Hình sự - Cấp bậc 1) như một hậu quả đối với trường hợp vi phạm nghiêm trọng.

- KỊCH BẢN 2 (TƯ VẤN DÂN SỰ, THỦ TỤC, CÁCH TÒA ÁN GIẢI QUYẾT)
  -> Mở đầu bằng: "Theo nguyên tắc thứ bậc hiệu lực pháp lý, chúng ta sẽ căn cứ chính vào [Văn bản Cấp 1/Cấp cao nhất]. Các văn bản hướng dẫn như [Văn bản Cấp thấp hơn] được sử dụng để làm rõ chi tiết..."
  -> TRÌNH TỰ SẮP XẾP BẮT BUỘC (TUYỆT ĐỐI KHÔNG LÀM TRÁI): Bạn PHẢI trình bày nội dung của Luật (Cấp bậc 1) ĐẦU TIÊN. Sau đó mới đến Nghị định (Cấp bậc 2). Và CUỐI CÙNG mới được phép trích dẫn Thông tư / Thông tư liên tịch (Cấp bậc 3).

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
- KHÔNG lặp lại "Căn cứ theo..." ở mỗi đoạn. KHÔNG chú thích nguồn ở cuối câu (VD: không dùng "(Căn cứ: Điều X...)").
- MỖI Khoản (1, 2...) và Điểm (a, b...) PHẢI XUỐNG DÒNG riêng biệt.

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
Nếu có "CĂN CỨ THAM CHIẾU BỔ TRỢ" và nó THỰC SỰ LIÊN QUAN ĐẾN CÂU HỎI, hãy nối mạch văn bằng câu: "Đồng thời, dẫn chiếu đến quy định tại [Tên Điều tham chiếu], nội dung này được quy định cụ thể như sau:" và tiếp tục dùng format trích dẫn Điều luật như ở Quy tắc 5.

7. KHÔNG BỊA ĐẶT:
Nếu thông tin pháp luật không có trong phần "CĂN CỨ PHÁP LÝ TỪ HỆ THỐNG", hãy trả lời rằng "Dựa trên thông tin hiện có, tôi không tìm thấy căn cứ pháp lý phù hợp để giải đáp câu hỏi của bạn. Bạn có thể cung cấp thêm chi tiết hoặc đặt câu hỏi khác không?"
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

@cl.on_message
async def main(message: cl.Message):
    input_text = message.content
    session_history = cl.user_session.get("session_history")

    async with cl.Step(name="Luồng phân tích câu hỏi") as p_step:
        # 1. Cập nhật câu hỏi dựa trên lịch sử
        # async with cl.Step(name="Query Updater", type="tool") as step1:
        #     step1.input = input_text
        #     updated_question = await query_update(input_text, session_history)
        #     step1.output = updated_question

        updated_question = input_text

        # 2. Lấy dữ liệu lần 1
        async with cl.Step(name="Router Agent", type="tool") as step2:
            step2.input = updated_question
            tool_response = await route_question(updated_question, tools, session_history)
            
            # Format lại tool_response để hiển thị đẹp hơn trên UI thay vì dùng JSON dumps thô
            formatted_output = ""
            for idx, res in enumerate(tool_response):
                formatted_output += f"**Kết quả từ Tool {idx + 1}:**\n"
                if isinstance(res, str):
                    formatted_output += f"{res}\n\n"
                else:
                    formatted_output += f"```json\n{json.dumps(res, ensure_ascii=False, indent=2)}\n```\n\n"
                    
            step2.output = formatted_output
        
        p_step.output = "Hoàn tất truy xuất ngữ cảnh pháp lý."

    current_context = list(session_history)
    current_context.append({
        "role": "system",
        "content": f"Dữ liệu lấy được từ hệ thống cho câu hỏi '{updated_question}': {json.dumps(tool_response, ensure_ascii=False)}"
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
        ans_step.input = "Context: " + str(tool_response)
        async for token in chat_stream(llm_messages):
            llm_response += token
            await msg.stream_token(token)
        ans_step.output = llm_response
    await msg.update()

    session_history.append({"role": "user", "content": input_text})
    session_history.append({"role": "assistant", "content": llm_response})
    cl.user_session.set("session_history", session_history)

