import re
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import date

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
def chuan_hoa_thoi_diem_su_kien(thoi_diem) -> Optional[str]:
    """
    Chuẩn hóa mốc thời gian sự kiện về YYYY-MM-DD.
    - Chỉ có năm (YYYY) -> YYYY-01-01
    - Chỉ có năm-tháng (YYYY-MM) -> YYYY-MM-01
    - Đã đủ ngày (YYYY-MM-DD) -> giữ nguyên
    """
    if thoi_diem is None:
        return None

    if isinstance(thoi_diem, date):
        return thoi_diem.strftime("%Y-%m-%d")

    s = str(thoi_diem).strip()
    if not s or s.lower() in ("null", "none"):
        return None

    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return s

    m = re.fullmatch(r"(\d{4})-(\d{1,2})", s)
    if m:
        year, month = m.groups()
        return f"{year}-{month.zfill(2)}-01"

    if re.fullmatch(r"\d{4}", s):
        return f"{s}-01-01"

    m = re.fullmatch(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", s)
    if m:
        day, month, year = m.groups()
        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"

    m = re.search(r"\b(19|20)\d{2}\b", s)
    if m:
        return f"{m.group()}-01-01"

    return s


def lay_target_date_tu_extraction(thoi_diem_su_kien, formatted_date: str):
    """Trả về (target_date, is_user_provide_date) sau khi chuẩn hóa mốc thời gian."""
    normalized = chuan_hoa_thoi_diem_su_kien(thoi_diem_su_kien)
    is_user_provide_date = bool(normalized)
    target_date = normalized or formatted_date
    return target_date, is_user_provide_date


class TrichXuatLuat(BaseModel):
    dieu_luat_ids: List[str] = Field(
        description="Danh sách ID điều luật cần dùng. (Có thể cần nhiều điều luật để trả lời đầy đủ câu hỏi)"
    )
    thoi_diem_su_kien: Optional[str] = Field(
        description=(
            "Năm/tháng/ngày xảy ra sự kiện trong câu hỏi. "
            "Định dạng 'YYYY-MM-DD'. Nếu người dùng chỉ nêu năm (vd: 2023), trả về 'YYYY' hoặc 'YYYY-01-01'. "
            "Nếu người dùng KHÔNG nhắc đến mốc thời gian, bắt buộc trả về null."
        ),
        default=None,
    )

    @field_validator("thoi_diem_su_kien", mode="before")
    @classmethod
    def _normalize_thoi_diem(cls, value):
        return chuan_hoa_thoi_diem_su_kien(value)

def _format_date_vn(date_str):
    """Chuyển đổi ngày từ YYYY-MM-DD sang DD-MM-YYYY."""
    if not date_str:
        return None
    try:
        if isinstance(date_str, date):
            return date_str.strftime("%d-%m-%Y")
        parts = str(date_str).split("-")
        if len(parts) == 3:
            return f"{parts[2]}-{parts[1]}-{parts[0]}"
    except:
        pass
    return None


def _extract_doc_name(node_id):
    """Trích xuất tên văn bản từ node ID (phần trước _Dieu_)."""
    if not node_id:
        return None
    match = re.match(r'^(.+?)_Dieu_', str(node_id))
    return match.group(1) if match else str(node_id)


def _collect_hieu_luc(items, doc_hieu_luc_map):
    """Thu thập thông tin hiệu lực từ danh sách items vào doc_hieu_luc_map."""

    def _add_doc(doc_id, ngay_hl, ngay_het):
        if not doc_id or not ngay_hl:
            return
        doc_name = _extract_doc_name(doc_id)
        if not doc_name:
            return
        if doc_name not in doc_hieu_luc_map:
            doc_hieu_luc_map[doc_name] = {"ngay_hieu_luc": ngay_hl, "ngay_het_hieu_luc": ngay_het}
        else:
            existing = doc_hieu_luc_map[doc_name]
            if ngay_het and not existing.get("ngay_het_hieu_luc"):
                existing["ngay_het_hieu_luc"] = ngay_het

    for item in items:
        node_id = item.get('id_thuc_te_ap_dung') or item.get('id')
        if node_id:
            _add_doc(node_id, item.get('ngay_hieu_luc'), item.get('ngay_het_hieu_luc'))

        if item.get('id_sua_doi'):
            _add_doc(
                item.get('id_sua_doi'),
                item.get('ngay_hieu_luc_sua_doi'),
                item.get('ngay_het_hieu_luc_sua_doi'),
            )


def chuan_hoa_Context_cho_LLM(neo4j_record, target_date, is_user_provide_date):
    data = neo4j_record['Context_Tho']

    context_sach = {
        "danh_sach_can_cu": [],
        "danh_sach_bo_tro": [],
        "FLAG_CANH_BAO_LICH_SU": "",
        "FLAG_CANH_BAO_THU_TU_UU_TIEN": "",
        "FLAG_CANH_BAO_SUA_DOI": ""
    }

    tat_ca_cap_bac = set()
    luat_da_het_hieu_luc = False
    doc_hieu_luc_map = {}

    # 1. Xử lý Căn cứ chính & Check Sửa đổi
    for item in data.get('can_cu_chinh', []):
        if not item.get('id_thuc_te_ap_dung'): continue

        tat_ca_cap_bac.add(item.get('cap_bac'))
        if item.get('het_hieu_luc'): luat_da_het_hieu_luc = True

        id_dang_dung = item['id_thuc_te_ap_dung']

        if item.get('id_sua_doi'):
            noidung_hien_thi = f"[{id_dang_dung}] (được sửa đổi, bổ sung bởi [{item.get('id_sua_doi')}]): {item.get('noidung_sua_doi')}"
            context_sach["FLAG_CANH_BAO_SUA_DOI"] = "CÓ_VĂN_BẢN_SỬA_ĐỔI"
        else:
            noidung_hien_thi = f"[{id_dang_dung}]: {item.get('noidung')}"

        context_sach["danh_sach_can_cu"].append({"cap_bac": item.get('cap_bac'), "text": noidung_hien_thi})

    _collect_hieu_luc(data.get('can_cu_chinh', []), doc_hieu_luc_map)

    # 2. Xử lý Hướng dẫn
    for hd in data.get('can_cu_huong_dan', []):
        if not hd.get('id'): continue
        tat_ca_cap_bac.add(hd.get('cap_bac'))
        if hd.get('id_sua_doi'):
            noidung_hd_hien_thi = f"[{hd['id']}] (được sửa đổi, bổ sung bởi [{hd['id_sua_doi']}]): {hd['noidung_sua_doi']}"
            context_sach["FLAG_CANH_BAO_SUA_DOI"] = "CÓ_VĂN_BẢN_SỬA_ĐỔI"
        else:
            noidung_hd_hien_thi = f"[{hd['id']}]: {hd['noidung']}"

        context_sach["danh_sach_can_cu"].append({"cap_bac": hd['cap_bac'], "text": noidung_hd_hien_thi})

    _collect_hieu_luc(data.get('can_cu_huong_dan', []), doc_hieu_luc_map)

    # 3. XỬ LÝ CĂN CỨ BỔ TRỢ (THAM CHIẾU)
    can_cu_bo_tro = data.get('can_cu_bo_tro', []) if 'can_cu_bo_tro' in data else []
    for bt in can_cu_bo_tro:
        if not bt.get('id'): continue
        context_sach["danh_sach_bo_tro"].append({"cap_bac": bt.get('cap_bac'), "text": f"[{bt.get('id')}]: {bt.get('noidung')}"})

    _collect_hieu_luc(can_cu_bo_tro, doc_hieu_luc_map)

    # 4. KÍCH HOẠT CÁC CỜ (FLAGS)
    if len(tat_ca_cap_bac) > 1:
        context_sach["FLAG_CANH_BAO_THU_TU_UU_TIEN"] = "CÓ_NHIỀU_CẤP_BẬC_PHÁP_LÝ"

    quy_dinh_hien_hanh = data.get('quy_dinh_hien_hanh_doi_chieu', []) if 'quy_dinh_hien_hanh_doi_chieu' in data else []
    if is_user_provide_date and luat_da_het_hieu_luc and quy_dinh_hien_hanh:
        luat_moi = ", ".join([str(i) for i in quy_dinh_hien_hanh if i])
        context_sach["FLAG_CANH_BAO_LICH_SU"] = f"ÁP DỤNG LUẬT CŨ TẠI THỜI ĐIỂM {target_date}. LUẬT HIỆN HÀNH BÂY GIỜ LÀ: {luat_moi}"

    # Sắp xếp danh sách căn cứ từ Cấp 1 -> Cấp 3
    context_sach["danh_sach_can_cu"] = sorted(context_sach["danh_sach_can_cu"], key=lambda x: x['cap_bac'])

    # Format lại thành string đưa vào Prompt
    final_context_string = f"--- THÔNG TIN CẢNH BÁO ---\n"
    final_context_string += f"Lịch sử: {context_sach['FLAG_CANH_BAO_LICH_SU']}\n"
    final_context_string += f"Ưu tiên: {context_sach['FLAG_CANH_BAO_THU_TU_UU_TIEN']}\n"
    final_context_string += f"Sửa đổi: {context_sach['FLAG_CANH_BAO_SUA_DOI']}\n\n"

    # THÔNG TIN HIỆU LỰC VĂN BẢN
    final_context_string += "--- THÔNG TIN HIỆU LỰC VĂN BẢN ---\n"
    for doc_name, dates in doc_hieu_luc_map.items():
        ngay_hl_fmt = _format_date_vn(dates["ngay_hieu_luc"])
        ngay_het_fmt = _format_date_vn(dates.get("ngay_het_hieu_luc"))
        line = f"- {doc_name}: Có hiệu lực từ ngày {ngay_hl_fmt}"
        if ngay_het_fmt:
            line += f" | HẾT HIỆU LỰC vào ngày {ngay_het_fmt}"
        final_context_string += line + "\n"
    final_context_string += "\n"

    final_context_string += "--- NỘI DUNG CĂN CỨ ---\n"
    for idx, item in enumerate(context_sach["danh_sach_can_cu"]):
        final_context_string += f"{idx+1}. (Cấp bậc {item['cap_bac']}): {item['text']}\n"

    if context_sach["danh_sach_bo_tro"]:
        final_context_string += "\n--- CĂN CỨ THAM CHIẾU BỔ TRỢ (ÁP DỤNG KÈM THEO) ---\n"
        for idx, item in enumerate(context_sach["danh_sach_bo_tro"]):
            final_context_string += f"{idx+1}. (Cấp bậc {item['cap_bac']}): {item['text']}\n"

    return final_context_string
