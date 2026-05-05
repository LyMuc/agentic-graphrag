import json
from config import chat
from utils import strip_code_fences

query_update_prompt = """
    Bạn là một chuyên gia trong việc tinh chỉnh câu hỏi pháp luật.
    Nhiệm vụ của bạn là bổ sung thông tin ngữ cảnh từ lịch sử trò chuyện vào câu hỏi hiện tại để nó trở nên rõ ràng và đầy đủ thông tin nhất.

    QUY TẮC QUAN TRỌNG:
    1. BẮT BUỘC giữ lại TOÀN BỘ các ý định/vấn đề mà người dùng đang hỏi. Nếu người dùng hỏi 2-3 vấn đề khác nhau trong một câu, bạn phải giữ nguyên số lượng vấn đề đó.
    2. Không được tự ý lược bỏ bất kỳ ý nào để làm câu hỏi ngắn gọn hơn.
    3. Chỉ chỉnh sửa để câu hỏi rõ nghĩa hơn (ví dụ: thay thế đại từ 'họ', 'nó' bằng danh từ cụ thể từ lịch sử).

    Định dạng JSON bắt buộc:
    {
        "question": "câu_hỏi_đầy_đủ_giữ_nguyên_mọi_ý_định"
    }
"""

async def query_update(input: str, answers: list[any]) -> str:
    messages = [
        {"role": "system", "content": query_update_prompt},
        *answers,
        {"role": "user", "content": f"Hãy tinh chỉnh câu hỏi này nhưng phải giữ trọn vẹn mọi ý định: '{input}'"},
    ]
    output = await chat(messages)
    try:
        jsonloads = json.loads(strip_code_fences(output))
        print('1 (Query Update - Đã sửa):', jsonloads)
        return jsonloads["question"]
    except:
        return input
