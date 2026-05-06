import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
import chainlit as cl
# Gọi data_layer để Chainlit thiết lập PostgreSQL connection lúc khởi động
from adapter import data_layer 
from chainlit import data as cl_data
from adapter.config import chat
from application.query_updater import query_update
from application.router import route_question

from adapter.retrievers.ket_hon.dieu_kien_ket_hon import dieu_kien_ket_hon, dieu_kien_ket_hon_description
from adapter.retrievers.ket_hon.dang_ky_ket_hon import dang_ky_ket_hon, dang_ky_ket_hon_description
from adapter.retrievers.ket_hon.ket_hon_trai_phap_luat import ket_hon_trai_phap_luat, ket_hon_trai_phap_luat_description
from adapter.retrievers.ket_hon.chung_song_nhu_vo_chong import chung_song_nhu_vo_chong, chung_song_nhu_vo_chong_description
from utils.general import text2cypher, text2cypher_description, answer_given, answer_given_description
from adapter.retrievers.vi_pham.xu_phat_vi_pham import xu_phat_vi_pham, xu_phat_vi_pham_description
from chainlit.types import ThreadDict
from typing import Dict, Optional

tools = {
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

NHIỆM VỤ ĐẶC BIỆT KHI XÂY DỰNG LẬP LUẬN:
Hãy kiểm tra phần "THÔNG TIN CẢNH BÁO" trong dữ liệu cung cấp và BẮT BUỘC áp dụng các quy tắc hành văn sau:

1. NẾU CÓ CẢNH BÁO "CÓ_NHIỀU_CẤP_BẬC_PHÁP_LÝ":
Bắt buộc sử dụng cấu trúc văn phong: "Có những căn cứ pháp lý sau đây để trả lời cho câu hỏi của bạn, nhưng theo thứ tự ưu tiên áp dụng văn bản quy phạm pháp luật, chúng ta sẽ căn cứ chính vào [Văn bản có Cấp bậc 1/Cấp cao nhất]. Các [Văn bản Cấp 2, 3...] được sử dụng để làm rõ chi tiết..."

2. NẾU CÓ CẢNH BÁO "CÓ_VĂN_BẢN_SỬA_ĐỔI":
Khi trích dẫn căn cứ, Bắt buộc sử dụng nguyên văn cấu trúc: "Theo quy định tại [Tên Điều/Khoản gốc], được sửa đổi, bổ sung bởi [Tên Điều/Khoản mới]..."

3. NẾU CÓ CẢNH BÁO LỊCH SỬ (ÁP DỤNG LUẬT CŨ):
Bắt buộc phải mở đầu phần tư vấn bằng câu: "Mặc dù quy định mới nhất hiện hành là [Tên luật mới], nhưng do sự kiện pháp lý của bạn xảy ra tại thời điểm [Thời gian quá khứ], nên theo nguyên tắc áp dụng pháp luật, chúng ta phải áp dụng căn cứ pháp lý tại thời điểm đó là [Tên Luật Cũ]. Cụ thể như sau..."

4. CHỈ CÓ 1 CĂN CỨ BÌNH THƯỜNG:
Hãy trả lời trực tiếp, rõ ràng, trích dẫn chuẩn xác tên Điều/Khoản và giải thích dễ hiểu cho người dùng.

5. KHÔNG BỊA ĐẶT:
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
    
    await cl.Message(
        content="*(Bạn đang xem lại một phiên tư vấn cũ trong lịch sử. Hệ thống đã khôi phục luồng trò chuyện!)*"
    ).send()

@cl.on_message
async def main(message: cl.Message):
    input_text = message.content
    session_history = cl.user_session.get("session_history")

    async with cl.Step(name="Luồng phân tích câu hỏi") as p_step:
        # 1. Cập nhật câu hỏi dựa trên lịch sử
        async with cl.Step(name="Query Updater", type="tool") as step1:
            step1.input = input_text
            updated_question = await query_update(input_text, session_history)
            step1.output = updated_question

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

    # Sinh câu trả lời cuối cùng
    async with cl.Step(name="Tổng hợp đáp án", type="llm") as ans_step:
        ans_step.input = "Context: " + str(tool_response)
        llm_response = await chat(
            [
                {"role": "system", "content": main_prompt},
                *current_context,
                {"role": "user", "content": f"Câu hỏi của người dùng: {input_text}"},
            ]
        )
        ans_step.output = llm_response

    session_history.append({"role": "user", "content": input_text})
    session_history.append({"role": "assistant", "content": llm_response})
    cl.user_session.set("session_history", session_history)

    await cl.Message(content=llm_response).send()

