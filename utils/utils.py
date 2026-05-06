import re
from pydantic import BaseModel, Field
from typing import List, Optional

def strip_code_fences(text: str) -> str:
    text = text.strip()
    # remove ```json or ``` and closing ```
    text = re.sub(r"^```json\s*|^```\s*|```$", "", text, flags=re.IGNORECASE).strip()
    return text

def strip_code_cypher(text: str) -> str:
    text = text.strip()
    # remove ```json or ``` and closing ```
    text = re.sub(r"^```(?:\w+)?\s*|```$", "", text, flags=re.IGNORECASE).strip()
    return text

# ==========================================
# CẤU TRÚC JSON LLM CHUNG CHO CÁC TOOL TRÍCH XUẤT
# ==========================================
class TrichXuatLuat(BaseModel):
    dieu_luat_ids: List[str] = Field(
        description="Danh sách ID điều luật cần dùng. (Có thể cần nhiều điều luật để trả lời đầy đủ câu hỏi)"
    )
    thoi_diem_su_kien: Optional[str] = Field(
        description="Năm/tháng/ngày xảy ra sự kiện trong câu hỏi. Định dạng 'YYYY-MM-DD'. Nếu người dùng KHÔNG nhắc đến mốc thời gian, bắt buộc trả về null.",
        default=None
    )

def chuan_hoa_Context_cho_LLM(neo4j_record, target_date, is_user_provide_date):
    data = neo4j_record['Context_Tho']

    context_sach = {
        "danh_sach_can_cu": [],
        "FLAG_CANH_BAO_LICH_SU": "",
        "FLAG_CANH_BAO_THU_TU_UU_TIEN": "",
        "FLAG_CANH_BAO_SUA_DOI": ""
    }

    tat_ca_cap_bac = set()
    luat_da_het_hieu_luc = False

    # 1. Xử lý Căn cứ chính & Check Sửa đổi
    for item in data['can_cu_chinh']:
        if not item.get('id_thuc_te_ap_dung'): continue

        tat_ca_cap_bac.add(item['cap_bac'])
        if item['het_hieu_luc']: luat_da_het_hieu_luc = True

        id_dang_dung = item['id_thuc_te_ap_dung']

        # [UPDATE MỚI] - Xử lý format nếu CÓ văn bản sửa đổi
        if item.get('id_sua_doi'):
            # ÉP LLM đọc cả 2 tên văn bản, nhưng NỘI DUNG đưa cho LLM là nội dung mới nhất đã sửa!
            noidung_hien_thi = f"[{id_dang_dung}] (được sửa đổi, bổ sung bởi [{item['id_sua_doi']}]): {item['noidung_sua_doi']}"
            context_sach["FLAG_CANH_BAO_SUA_DOI"] = "CÓ_VĂN_BẢN_SỬA_ĐỔI"
        else:
            # Luật nguyên bản, không bị ai sửa
            noidung_hien_thi = f"[{id_dang_dung}]: {item['noidung']}"

        context_sach["danh_sach_can_cu"].append({"cap_bac": item['cap_bac'], "text": noidung_hien_thi})

    # 2. Xử lý Hướng dẫn
    for hd in data['can_cu_huong_dan']:
        if not hd.get('id'): continue
        tat_ca_cap_bac.add(hd['cap_bac'])
        context_sach["danh_sach_can_cu"].append({"cap_bac": hd['cap_bac'], "text": f"[{hd['id']}]: {hd['noidung']}"})

    # 3. KÍCH HOẠT CÁC CỜ (FLAGS)
    # Cờ Ưu tiên
    if len(tat_ca_cap_bac) > 1:
        context_sach["FLAG_CANH_BAO_THU_TU_UU_TIEN"] = "CÓ_NHIỀU_CẤP_BẬC_PHÁP_LÝ"

    # Cờ Lịch sử
    if is_user_provide_date and luat_da_het_hieu_luc and data['quy_dinh_hien_hanh_doi_chieu']:
        luat_moi = ", ".join([str(i) for i in data['quy_dinh_hien_hanh_doi_chieu'] if i])
        context_sach["FLAG_CANH_BAO_LICH_SU"] = f"ÁP DỤNG LUẬT CŨ TẠI THỜI ĐIỂM {target_date}. LUẬT HIỆN HÀNH BÂY GIỜ LÀ: {luat_moi}"

    # Sắp xếp danh sách căn cứ từ Cấp 1 -> Cấp 3
    context_sach["danh_sach_can_cu"] = sorted(context_sach["danh_sach_can_cu"], key=lambda x: x['cap_bac'])

    # Format lại thành string đưa vào Prompt
    final_context_string = f"--- THÔNG TIN CẢNH BÁO ---\n"
    final_context_string += f"Lịch sử: {context_sach['FLAG_CANH_BAO_LICH_SU']}\n"
    final_context_string += f"Ưu tiên: {context_sach['FLAG_CANH_BAO_THU_TU_UU_TIEN']}\n"
    final_context_string += f"Sửa đổi: {context_sach['FLAG_CANH_BAO_SUA_DOI']}\n\n"
    final_context_string += "--- NỘI DUNG CĂN CỨ ---\n"
    for idx, item in enumerate(context_sach["danh_sach_can_cu"]):
        final_context_string += f"{idx+1}. (Cấp bậc {item['cap_bac']}): {item['text']}\n"

    return final_context_string
