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


def _dedupe_maps_by_id(items: list, key: str = "id") -> list:
    """Gộp list map Cypher, giữ một bản ghi đầu tiên cho mỗi id."""
    seen = set()
    out: list = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        item_id = item.get(key)
        if not item_id or item_id in seen:
            continue
        seen.add(item_id)
        out.append(item)
    return out


def _filter_van_ban_thay_the_thuc(
    quy_dinh_hien_hanh: list,
    can_cu_chinh: list,
    flag_lich_su: str,
) -> list:
    """Chỉ giữ ID thay thế thật — loại ID trùng căn cứ chính khi không có cảnh báo lịch sử."""
    raw = [str(i) for i in quy_dinh_hien_hanh if i]
    if not raw:
        return []
    if flag_lich_su:
        return raw
    can_cu_ids = {
        str(item.get("id_thuc_te_ap_dung"))
        for item in can_cu_chinh
        if item.get("id_thuc_te_ap_dung")
    }
    return [i for i in raw if i not in can_cu_ids]


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
        "danh_sach_huong_dan": [],
        "danh_sach_van_ban_thay_the": [],
        "danh_sach_mau_thuan": [],
        "FLAG_CANH_BAO_LICH_SU": "",
        "FLAG_CANH_BAO_THU_TU_UU_TIEN": "",
        "FLAG_CANH_BAO_SUA_DOI": "",
        "FLAG_MAU_THUAN": "",
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

    # 2. Xử lý Hướng dẫn (dedup safety-net theo id)
    for hd in _dedupe_maps_by_id(data.get('can_cu_huong_dan', [])):
        if not hd.get('id'): continue
        tat_ca_cap_bac.add(hd.get('cap_bac'))
        if hd.get('id_sua_doi'):
            noidung_hd_hien_thi = f"[{hd['id']}] (được sửa đổi, bổ sung bởi [{hd['id_sua_doi']}]): {hd['noidung_sua_doi']}"
            context_sach["FLAG_CANH_BAO_SUA_DOI"] = "CÓ_VĂN_BẢN_SỬA_ĐỔI"
        else:
            noidung_hd_hien_thi = f"[{hd['id']}]: {hd['noidung']}"

        context_sach["danh_sach_huong_dan"].append({"cap_bac": hd['cap_bac'], "text": noidung_hd_hien_thi})

    _collect_hieu_luc(data.get('can_cu_huong_dan', []), doc_hieu_luc_map)

    # 3. XỬ LÝ CĂN CỨ BỔ TRỢ (THAM CHIẾU)
    can_cu_bo_tro = _dedupe_maps_by_id(
        data.get('can_cu_bo_tro', []) if 'can_cu_bo_tro' in data else []
    )
    for bt in can_cu_bo_tro:
        if not bt.get('id'): continue
        context_sach["danh_sach_bo_tro"].append({"cap_bac": bt.get('cap_bac'), "text": f"[{bt.get('id')}]: {bt.get('noidung')}"})

    _collect_hieu_luc(can_cu_bo_tro, doc_hieu_luc_map)

    # 3b. XỬ LÝ MÂU THUẪN (MAU_THUAN_VOI)
    seen_mau_thuan = set()
    can_cu_mau_thuan_raw = data.get('can_cu_mau_thuan', []) if 'can_cu_mau_thuan' in data else []
    for mt in can_cu_mau_thuan_raw:
        if not isinstance(mt, dict):
            continue
        id_nguon = mt.get('id_nguon')
        id_dich = mt.get('id_dich')
        if not id_nguon or not id_dich:
            continue
        pair_key = (id_nguon, id_dich)
        if pair_key in seen_mau_thuan:
            continue
        seen_mau_thuan.add(pair_key)
        context_sach["danh_sach_mau_thuan"].append({
            "id_nguon": id_nguon,
            "id_dich": id_dich,
            "noidung_giai_thich": mt.get('noidung_giai_thich'),
            "noidung_dich": mt.get('noidung_dich'),
            "cap_bac": mt.get('cap_bac'),
        })
        _collect_hieu_luc([{
            'id': id_dich,
            'ngay_hieu_luc': mt.get('ngay_hieu_luc'),
            'ngay_het_hieu_luc': mt.get('ngay_het_hieu_luc'),
        }], doc_hieu_luc_map)

    if context_sach["danh_sach_mau_thuan"]:
        context_sach["FLAG_MAU_THUAN"] = "CO_MAU_THUAN"

    # 4. KÍCH HOẠT CÁC CỜ (FLAGS)
    if len(tat_ca_cap_bac) > 1:
        context_sach["FLAG_CANH_BAO_THU_TU_UU_TIEN"] = "CÓ_NHIỀU_CẤP_BẬC_PHÁP_LÝ"

    quy_dinh_hien_hanh = data.get('quy_dinh_hien_hanh_doi_chieu', []) if 'quy_dinh_hien_hanh_doi_chieu' in data else []
    context_sach["danh_sach_van_ban_thay_the"] = _filter_van_ban_thay_the_thuc(
        quy_dinh_hien_hanh,
        data.get('can_cu_chinh', []),
        context_sach["FLAG_CANH_BAO_LICH_SU"],
    )
    if is_user_provide_date and luat_da_het_hieu_luc and context_sach["danh_sach_van_ban_thay_the"]:
        luat_moi = ", ".join(context_sach["danh_sach_van_ban_thay_the"])
        context_sach["FLAG_CANH_BAO_LICH_SU"] = f"ÁP DỤNG LUẬT CŨ TẠI THỜI ĐIỂM {target_date}. LUẬT HIỆN HÀNH BÂY GIỜ LÀ: {luat_moi}"

    # Sắp xếp danh sách căn cứ từ Cấp 1 -> Cấp 3
    context_sach["danh_sach_can_cu"] = sorted(context_sach["danh_sach_can_cu"], key=lambda x: x['cap_bac'])
    context_sach["danh_sach_huong_dan"] = sorted(context_sach["danh_sach_huong_dan"], key=lambda x: x['cap_bac'])

    # Format lại thành string đưa vào Prompt
    final_context_string = f"--- THÔNG TIN CẢNH BÁO ---\n"
    final_context_string += f"Lịch sử: {context_sach['FLAG_CANH_BAO_LICH_SU']}\n"
    final_context_string += f"Ưu tiên: {context_sach['FLAG_CANH_BAO_THU_TU_UU_TIEN']}\n"
    final_context_string += f"Sửa đổi: {context_sach['FLAG_CANH_BAO_SUA_DOI']}\n"
    final_context_string += f"Mâu thuẫn: {context_sach['FLAG_MAU_THUAN']}\n\n"

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

    final_context_string += "--- CĂN CỨ CHÍNH ---\n"
    for idx, item in enumerate(context_sach["danh_sach_can_cu"]):
        final_context_string += f"{idx+1}. (Cấp bậc {item['cap_bac']}): {item['text']}\n"

    if context_sach["danh_sach_bo_tro"]:
        final_context_string += "\n--- CĂN CỨ THAM CHIẾU BỔ TRỢ (ÁP DỤNG KÈM THEO) ---\n"
        for idx, item in enumerate(context_sach["danh_sach_bo_tro"]):
            final_context_string += f"{idx+1}. (Cấp bậc {item['cap_bac']}): {item['text']}\n"

    if context_sach["danh_sach_huong_dan"]:
        final_context_string += "\n--- CĂN CỨ HƯỚNG DẪN ---\n"
        for idx, item in enumerate(context_sach["danh_sach_huong_dan"]):
            final_context_string += f"{idx+1}. (Cấp bậc {item['cap_bac']}): {item['text']}\n"

    if context_sach["danh_sach_van_ban_thay_the"]:
        final_context_string += "\n--- VĂN BẢN THAY THẾ ---\n"
        for idx, item in enumerate(context_sach["danh_sach_van_ban_thay_the"]):
            final_context_string += f"{idx+1}. {item}\n"

    if context_sach["danh_sach_mau_thuan"]:
        final_context_string += "\n--- THÔNG TIN MÂU THUẪN PHÁP LÝ ---\n"
        for idx, item in enumerate(context_sach["danh_sach_mau_thuan"]):
            final_context_string += (
                f"{idx+1}. Điều khoản nguồn: [{item['id_nguon']}]\n"
                f"   Điều khoản mâu thuẫn: [{item['id_dich']}]\n"
                f"   Giải thích mâu thuẫn: {item['noidung_giai_thich']}\n"
                f"   Nội dung điều khoản mâu thuẫn (Cấp bậc {item['cap_bac']}): "
                f"[{item['id_dich']}]: {item['noidung_dich']}\n"
            )

    return final_context_string


def _unique_non_empty(values):
    result = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result


def extract_raw_ids_from_context(context_tho):
    """Trích xuất các ID cần kiểm tra từ kết quả Cypher chưa chuẩn hóa."""
    can_cu_chinh = [
        item.get("id_thuc_te_ap_dung") or item.get("id")
        for item in context_tho.get("can_cu_chinh", [])
        if item
    ]
    can_cu_huong_dan = [
        item.get("id")
        for item in context_tho.get("can_cu_huong_dan", [])
        if item
    ]
    can_cu_bo_tro = [
        item.get("id")
        for item in context_tho.get("can_cu_bo_tro", [])
        if item
    ]
    can_cu_mau_thuan = [
        item.get("id_dich")
        for item in context_tho.get("can_cu_mau_thuan", [])
        if item
    ]

    return {
        "can_cu_chinh": _unique_non_empty(can_cu_chinh),
        "can_cu_huong_dan": _unique_non_empty(can_cu_huong_dan),
        "can_cu_bo_tro": _unique_non_empty(can_cu_bo_tro),
        "can_cu_mau_thuan": _unique_non_empty(can_cu_mau_thuan),
    }


def chuan_hoa_ket_qua_retriever(records, target_date, is_user_provide_date):
    """Trả về đồng nhất raw_ids + contexts cho mọi retriever."""
    raw_ids = {
        "can_cu_chinh": [],
        "can_cu_huong_dan": [],
        "can_cu_bo_tro": [],
        "can_cu_mau_thuan": [],
    }
    contexts = []

    for record in records:
        context_tho = record["Context_Tho"]
        ids = extract_raw_ids_from_context(context_tho)
        for key, values in ids.items():
            raw_ids[key] = _unique_non_empty([*raw_ids[key], *values])

        contexts.append(chuan_hoa_Context_cho_LLM(record, target_date, is_user_provide_date))

    return {
        "raw_ids": raw_ids,
        "contexts": contexts,
    }
