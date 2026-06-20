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


_DIEU_ID_RE = re.compile(r"^(.+?_Dieu_\d+[a-zA-Z]?)")


def _dieu_level_id(node_id):
    """Roll-up ID Khoản/Điểm về cấp Điều (vd. ..._Dieu_30_Khoan_1 -> ..._Dieu_30)."""
    if not node_id:
        return None
    s = str(node_id).strip()
    match = _DIEU_ID_RE.match(s)
    return match.group(1) if match else s


_LOAI_TAC_DONG_LABEL = {
    "SUA_DOI_BOI": "sửa đổi, bổ sung",
    "HUONG_DAN_BOI": "hướng dẫn",
    "SUA_DOI_HUONG_DAN": "sửa đổi, bổ sung (văn bản hướng dẫn)",
    "THAY_THE_BOI": "thay thế",
    "BAI_BO": "bãi bỏ",
    "HET_HIEU_LUC": "hết hiệu lực theo lịch",
}


def _format_lien_ket_sap_hieu_luc(pairs: list) -> str:
    """Ghép các cặp (văn bản sắp HL, căn cứ bị tác động) thành một dòng — gộp cấp Điều."""
    seen = set()
    parts: list[str] = []
    for pair in pairs or []:
        if not isinstance(pair, dict):
            continue
        id_vb = _dieu_level_id(pair.get("id_van_ban"))
        id_goc = _dieu_level_id(pair.get("id_duoc_tac_dong"))
        loai = pair.get("loai_tac_dong")
        if not id_vb or not id_goc:
            continue
        key = (id_vb, id_goc, loai)
        if key in seen:
            continue
        seen.add(key)
        if str(loai) == "HET_HIEU_LUC":
            parts.append(f"{id_goc} hết hiệu lực theo lịch")
            continue
        label = _LOAI_TAC_DONG_LABEL.get(str(loai), str(loai or "tác động"))
        parts.append(f"{id_vb} {label} [{id_goc}]")
    return ", ".join(parts)


def _format_lien_ket_hien_hanh(pairs: list) -> str:
    """Ghép các cặp (văn bản hiện hành thay thế, căn cứ cũ) — gộp cấp Điều."""
    seen = set()
    parts: list[str] = []
    for pair in pairs or []:
        if not isinstance(pair, dict):
            continue
        id_hh = _dieu_level_id(pair.get("id_hien_hanh"))
        id_goc = _dieu_level_id(pair.get("id_duoc_thay_the"))
        if not id_hh or not id_goc:
            continue
        key = (id_hh, id_goc)
        if key in seen:
            continue
        seen.add(key)
        parts.append(f"{id_hh} thay thế [{id_goc}]")
    return ", ".join(parts)


def _format_lien_ket_huong_dan(pairs: list) -> str:
    """Ghép các cặp (văn bản hướng dẫn, căn cứ được hướng dẫn) thành một dòng — gộp cấp Điều."""
    seen = set()
    parts: list[str] = []
    for pair in pairs or []:
        if not isinstance(pair, dict):
            continue
        id_hd = _dieu_level_id(pair.get("id_huong_dan"))
        id_goc = _dieu_level_id(pair.get("id_duoc_huong_dan"))
        if not id_hd or not id_goc:
            continue
        key = (id_hd, id_goc)
        if key in seen:
            continue
        seen.add(key)
        parts.append(f"{id_hd} hướng dẫn [{id_goc}]")
    return ", ".join(parts)


def _provision_key(item: dict) -> tuple[str, str]:
    """Khóa dedupe xuyên mục: (node_id, id_sua_doi hoặc rỗng)."""
    node_id = str(item.get("id_thuc_te_ap_dung") or item.get("id") or "")
    sua_doi = str(item.get("id_sua_doi") or "")
    return (node_id, sua_doi)


def _is_duplicate_provision(seen: set, item: dict) -> bool:
    key = _provision_key(item)
    if not key[0]:
        return True
    return key in seen


def _to_dieu_id(node_id) -> str | None:
    """Roll-up ID về cấp Điều; trả None nếu không phải node Điều/Khoản/Điểm."""
    if not node_id:
        return None
    rolled = _dieu_level_id(str(node_id).strip())
    if rolled and _DIEU_ID_RE.match(rolled):
        return rolled
    return None


def _collect_dieu_ids_from_context(data: dict) -> set[str]:
    """Gom ID Điều từ Context_Tho thô (dùng cho test/diagnostic, không cho BẢNG LINK)."""
    raw_ids: list[str | None] = []

    def _add(*values) -> None:
        raw_ids.extend(values)

    for item in data.get("can_cu_chinh", []) or []:
        if not isinstance(item, dict):
            continue
        _add(item.get("id_thuc_te_ap_dung"), item.get("id_goc_tu_router"), item.get("id_sua_doi"))
    for item in data.get("can_cu_huong_dan", []) or []:
        if not isinstance(item, dict):
            continue
        _add(item.get("id"), item.get("id_sua_doi"))
    for item in data.get("can_cu_bo_tro", []) or []:
        if isinstance(item, dict):
            _add(item.get("id"))
    for item in data.get("can_cu_mau_thuan", []) or []:
        if isinstance(item, dict):
            _add(item.get("id_nguon"), item.get("id_dich"))
    for item in data.get("can_cu_sap_hieu_luc", []) or []:
        if isinstance(item, dict):
            _add(item.get("id"))
    for node_id in data.get("quy_dinh_hien_hanh_doi_chieu", []) or []:
        _add(node_id)
    for pair in data.get("lien_ket_hien_hanh", []) or []:
        if isinstance(pair, dict):
            _add(pair.get("id_hien_hanh"), pair.get("id_duoc_thay_the"))
    for pair in data.get("lien_ket_sap_hieu_luc", []) or []:
        if isinstance(pair, dict):
            _add(pair.get("id_van_ban"), pair.get("id_duoc_tac_dong"))
    for pair in data.get("lien_ket_huong_dan", []) or []:
        if isinstance(pair, dict):
            _add(pair.get("id_huong_dan"), pair.get("id_duoc_huong_dan"))

    dieu_ids: set[str] = set()
    for node_id in raw_ids:
        dieu_id = _to_dieu_id(node_id)
        if dieu_id:
            dieu_ids.add(dieu_id)
    return dieu_ids


def _collect_dieu_ids_for_bang_link(
    *,
    can_cu_chinh_kept: list,
    can_cu_huong_dan_kept: list,
    can_cu_bo_tro_kept: list,
    mau_thuan_kept: list,
    sap_hieu_luc_kept: list,
    lien_ket_hien_hanh_kept: list,
    van_ban_thay_the_ids: list,
) -> set[str]:
    """Gom ID Điều chỉ từ căn cứ đã qua dedupe — khớp nội dung gửi LLM."""
    raw_ids: list[str | None] = []

    def _add(*values) -> None:
        raw_ids.extend(values)

    for item in can_cu_chinh_kept:
        if isinstance(item, dict):
            _add(item.get("id_thuc_te_ap_dung"), item.get("id_sua_doi"))
    for item in can_cu_huong_dan_kept:
        if isinstance(item, dict):
            _add(item.get("id"), item.get("id_sua_doi"))
    for item in can_cu_bo_tro_kept:
        if isinstance(item, dict):
            _add(item.get("id"))
    for item in mau_thuan_kept:
        if isinstance(item, dict):
            _add(item.get("id_nguon"), item.get("id_dich"))
    for item in sap_hieu_luc_kept:
        if isinstance(item, dict):
            _add(item.get("id"))
    for pair in lien_ket_hien_hanh_kept:
        if isinstance(pair, dict):
            _add(pair.get("id_hien_hanh"))
    for node_id in van_ban_thay_the_ids or []:
        _add(node_id)

    dieu_ids: set[str] = set()
    for node_id in raw_ids:
        dieu_id = _to_dieu_id(node_id)
        if dieu_id:
            dieu_ids.add(dieu_id)
    return dieu_ids


def _fetch_tvpl_links(dieu_ids: set[str]) -> dict[str, str]:
    """Tra link TVPL trên node pháp lý (ưu tiên cấp Điều) theo batch."""
    if not dieu_ids:
        return {}
    try:
        from adapter.config import driver  # lazy import tránh vòng phụ thuộc lúc import utils
    except ImportError:
        return {}
    cypher = """
    MATCH (n)
    WHERE (n:DieuLuat OR n:DieuKhoanLuat OR n:DieuKhoanDiemLuat)
      AND n.id IN $ids
      AND n.link IS NOT NULL
    RETURN n.id AS id, n.link AS link
    """
    try:
        records, _, _ = driver.execute_query(cypher, ids=list(dieu_ids))
        return {r["id"]: r["link"] for r in records if r.get("id") and r.get("link")}
    except Exception:
        return {}


def _format_bang_link_trich_dan(link_map: dict[str, str]) -> str:
    if not link_map:
        return ""
    lines = [
        "--- BẢNG LINK TRÍCH DẪN (TVPL) ---",
        "Chỉ liệt kê cấp Điều. Khi trích dẫn Khoản/Điểm, dùng link của Điều cha tương ứng.",
    ]
    for dieu_id in sorted(link_map):
        lines.append(f"- [{dieu_id}] → {link_map[dieu_id]}")
    return "\n".join(lines) + "\n"


def _register_provision(seen: set, item: dict) -> bool:
    """Đăng ký provision; trả True nếu khóa mới (nên append), False nếu trùng."""
    key = _provision_key(item)
    if not key[0]:
        return False
    if key in seen:
        return False
    seen.add(key)
    return True


def _seen_node_ids(seen_provisions: set) -> set[str]:
    return {key[0] for key in seen_provisions if key[0]}


_LOAI_TAC_DONG_VAN_BAN_MOI = frozenset({
    "SUA_DOI_BOI", "HUONG_DAN_BOI", "SUA_DOI_HUONG_DAN", "THAY_THE_BOI", "BAI_BO",
})


def _filter_sap_hieu_luc_noi_dung(items: list) -> list:
    """Chỉ giữ nội dung văn bản mới sắp HL; bỏ HET_HIEU_LUC (chỉ có trên dòng liên kết)."""
    return [
        item for item in (items or [])
        if isinstance(item, dict)
        and item.get("id")
        and str(item.get("loai_tac_dong") or "") in _LOAI_TAC_DONG_VAN_BAN_MOI
    ]


def _filter_van_ban_thay_the_thuc(
    quy_dinh_hien_hanh: list,
    seen_provisions: set,
    flag_lich_su: str,
) -> list:
    """Chỉ giữ ID thay thế thật — loại ID đã có trong registry khi không có cảnh báo lịch sử."""
    raw = [str(i) for i in quy_dinh_hien_hanh if i]
    if not raw:
        return []
    if flag_lich_su:
        return raw
    return [i for i in raw if i not in _seen_node_ids(seen_provisions)]


def _filter_lien_ket_hien_hanh(
    pairs: list,
    seen_provisions: set,
    flag_lich_su: str,
) -> list[dict]:
    """Lọc cặp thay thế hiện hành — bỏ cặp trùng provision đã có trong registry."""
    out: list[dict] = []
    seen_pair: set[tuple[str, str]] = set()
    for pair in pairs or []:
        if not isinstance(pair, dict):
            continue
        id_hh = pair.get("id_hien_hanh")
        id_goc = pair.get("id_duoc_thay_the")
        if not id_hh or not id_goc:
            continue
        key = (str(id_hh), str(id_goc))
        if key in seen_pair:
            continue
        if not flag_lich_su and str(id_hh) in _seen_node_ids(seen_provisions):
            continue
        # So khớp cấp Điều (Khoản/Điểm → Điều) — tắt: không cần ẩn section khi id_hien_hanh
        # trùng provision đã có ở cấp con; chỉ giữ lọc ID node khớp chính xác ở trên.
        # seen_nodes = _seen_node_ids(seen_provisions)
        # seen_dieu = {_dieu_level_id(n) for n in seen_nodes if _dieu_level_id(n)}
        # if not flag_lich_su:
        #     id_hh_dieu = _dieu_level_id(id_hh)
        #     if str(id_hh) in seen_nodes or (id_hh_dieu and id_hh_dieu in seen_dieu):
        #         continue
        seen_pair.add(key)
        out.append(pair)
    return out


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


def chuan_hoa_Context_cho_LLM(
    neo4j_record,
    target_date,
    is_user_provide_date,
    citation_links=None,
):
    """Chuẩn hóa ``Context_Tho`` thành văn bản căn cứ pháp lý cho LLM.

    Args:
        neo4j_record: Mapping chứa khóa ``Context_Tho`` từ kết quả Neo4j.
        target_date: Ngày áp dụng pháp luật theo định dạng ``YYYY-MM-DD``.
        is_user_provide_date: ``True`` khi người dùng nêu rõ mốc thời gian;
            dùng để bật cảnh báo lịch sử và tắt cảnh báo luật sắp hiệu lực.
        citation_links: Mapping tùy chọn từ ID cấp Điều tới URL TVPL. Nếu
            không truyền, hàm tự tải link từ Neo4j như hành vi cũ.

    Returns:
        Chuỗi context đã định dạng gồm cảnh báo, hiệu lực, căn cứ chính,
        hướng dẫn, bổ trợ, mâu thuẫn, luật sắp hiệu lực và link trích dẫn.
    """
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
        "FLAG_VAN_BAN_SAP_HIEU_LUC": "",
        "danh_sach_sap_hieu_luc": [],
    }

    tat_ca_cap_bac = set()
    luat_da_het_hieu_luc = False
    doc_hieu_luc_map = {}
    seen_provisions: set[tuple[str, str]] = set()

    # 1. Xử lý Căn cứ chính & Check Sửa đổi
    can_cu_chinh_kept: list = []
    for item in data.get('can_cu_chinh', []):
        if not item.get('id_thuc_te_ap_dung'):
            continue
        if not _register_provision(seen_provisions, item):
            continue

        can_cu_chinh_kept.append(item)
        tat_ca_cap_bac.add(item.get('cap_bac'))
        if item.get('het_hieu_luc'):
            luat_da_het_hieu_luc = True

        id_dang_dung = item['id_thuc_te_ap_dung']

        if item.get('id_sua_doi'):
            noidung_hien_thi = f"[{id_dang_dung}] (được sửa đổi, bổ sung bởi [{item.get('id_sua_doi')}]): {item.get('noidung_sua_doi')}"
            context_sach["FLAG_CANH_BAO_SUA_DOI"] = "CÓ_VĂN_BẢN_SỬA_ĐỔI"
        else:
            noidung_hien_thi = f"[{id_dang_dung}]: {item.get('noidung')}"

        context_sach["danh_sach_can_cu"].append({"cap_bac": item.get('cap_bac'), "text": noidung_hien_thi})

    _collect_hieu_luc(can_cu_chinh_kept, doc_hieu_luc_map)

    # 2. Xử lý Hướng dẫn — giữ đủ Khoản/Điểm; dòng liên kết vẫn gộp cấp Điều
    can_cu_huong_dan_kept: list = []
    for hd in data.get('can_cu_huong_dan', []):
        if not hd.get('id'):
            continue
        if not _register_provision(seen_provisions, hd):
            continue

        can_cu_huong_dan_kept.append(hd)
        tat_ca_cap_bac.add(hd.get('cap_bac'))
        if hd.get('id_sua_doi'):
            noidung_hd_hien_thi = f"[{hd['id']}] (được sửa đổi, bổ sung bởi [{hd['id_sua_doi']}]): {hd['noidung_sua_doi']}"
            context_sach["FLAG_CANH_BAO_SUA_DOI"] = "CÓ_VĂN_BẢN_SỬA_ĐỔI"
        else:
            noidung_hd_hien_thi = f"[{hd['id']}]: {hd['noidung']}"

        context_sach["danh_sach_huong_dan"].append({"cap_bac": hd['cap_bac'], "text": noidung_hd_hien_thi})

    _collect_hieu_luc(can_cu_huong_dan_kept, doc_hieu_luc_map)

    # 3. XỬ LÝ CĂN CỨ BỔ TRỢ (THAM CHIẾU)
    can_cu_bo_tro_kept: list = []
    for bt in data.get('can_cu_bo_tro', []) if 'can_cu_bo_tro' in data else []:
        if not bt.get('id'):
            continue
        if not _register_provision(seen_provisions, bt):
            continue

        can_cu_bo_tro_kept.append(bt)
        context_sach["danh_sach_bo_tro"].append({
            "cap_bac": bt.get('cap_bac'),
            "text": f"[{bt.get('id')}]: {bt.get('noidung')}",
        })

    _collect_hieu_luc(can_cu_bo_tro_kept, doc_hieu_luc_map)

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
    lien_ket_hh_raw = data.get("lien_ket_hien_hanh", []) if "lien_ket_hien_hanh" in data else []
    lien_ket_hh = _filter_lien_ket_hien_hanh(
        lien_ket_hh_raw,
        seen_provisions,
        context_sach["FLAG_CANH_BAO_LICH_SU"],
    )
    context_sach["lien_ket_hien_hanh"] = lien_ket_hh
    context_sach["danh_sach_van_ban_thay_the"] = _filter_van_ban_thay_the_thuc(
        quy_dinh_hien_hanh,
        seen_provisions,
        context_sach["FLAG_CANH_BAO_LICH_SU"],
    )
    if is_user_provide_date and luat_da_het_hieu_luc:
        if lien_ket_hh:
            luat_moi = ", ".join(
                f"{_dieu_level_id(p['id_hien_hanh'])} thay thế [{_dieu_level_id(p['id_duoc_thay_the'])}]"
                for p in lien_ket_hh
            )
        elif context_sach["danh_sach_van_ban_thay_the"]:
            luat_moi = ", ".join(context_sach["danh_sach_van_ban_thay_the"])
        else:
            luat_moi = ""
        if luat_moi:
            context_sach["FLAG_CANH_BAO_LICH_SU"] = (
                f"ÁP DỤNG LUẬT CŨ TẠI THỜI ĐIỂM {target_date}. LUẬT HIỆN HÀNH BÂY GIỜ LÀ: {luat_moi}"
            )

    # 5. VĂN BẢN SẮP CÓ HIỆU LỰC (chỉ khi không nêu mốc thời gian)
    can_cu_sap_kept: list = []
    can_cu_sap_raw = data.get("can_cu_sap_hieu_luc", []) if "can_cu_sap_hieu_luc" in data else []
    if not is_user_provide_date and can_cu_sap_raw:
        context_sach["FLAG_VAN_BAN_SAP_HIEU_LUC"] = "CÓ_VĂN_BẢN_SẮP_CÓ_HIỆU_LỰC"
        for sap in _filter_sap_hieu_luc_noi_dung(can_cu_sap_raw):
            if not _register_provision(seen_provisions, sap):
                continue
            can_cu_sap_kept.append(sap)
            context_sach["danh_sach_sap_hieu_luc"].append({
                "cap_bac": sap.get("cap_bac"),
                "text": f"[{sap['id']}]: {sap.get('noidung') or ''}",
            })

    # Sắp xếp danh sách căn cứ từ Cấp 1 -> Cấp 3
    context_sach["danh_sach_can_cu"] = sorted(context_sach["danh_sach_can_cu"], key=lambda x: x['cap_bac'])
    context_sach["danh_sach_huong_dan"] = sorted(
        context_sach["danh_sach_huong_dan"],
        key=lambda x: (x.get("cap_bac") or 0, str(x.get("text", ""))),
    )

    # Format lại thành string đưa vào Prompt
    final_context_string = f"--- THÔNG TIN CẢNH BÁO ---\n"
    final_context_string += f"Lịch sử: {context_sach['FLAG_CANH_BAO_LICH_SU']}\n"
    final_context_string += f"Ưu tiên: {context_sach['FLAG_CANH_BAO_THU_TU_UU_TIEN']}\n"
    final_context_string += f"Sửa đổi: {context_sach['FLAG_CANH_BAO_SUA_DOI']}\n"
    final_context_string += f"Mâu thuẫn: {context_sach['FLAG_MAU_THUAN']}\n"
    final_context_string += f"Sắp hiệu lực: {context_sach['FLAG_VAN_BAN_SAP_HIEU_LUC']}\n\n"

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
        lien_ket_line = _format_lien_ket_huong_dan(data.get('lien_ket_huong_dan', []))
        if lien_ket_line:
            final_context_string += f"{lien_ket_line}\n"
        for idx, item in enumerate(context_sach["danh_sach_huong_dan"]):
            final_context_string += f"{idx+1}. (Cấp bậc {item['cap_bac']}): {item['text']}\n"

    if context_sach["FLAG_VAN_BAN_SAP_HIEU_LUC"]:
        final_context_string += (
            "\n--- VĂN BẢN ĐÃ BAN HÀNH, CHƯA CÓ HIỆU LỰC "
            "(CHỈ ĐỂ CẢNH BÁO, KHÔNG DÙNG LÀM CĂN CỨ TRẢ LỜI CHÍNH) ---\n"
        )
        lien_ket_sap_line = _format_lien_ket_sap_hieu_luc(data.get("lien_ket_sap_hieu_luc", []))
        if lien_ket_sap_line:
            final_context_string += f"{lien_ket_sap_line}\n"
        if context_sach["danh_sach_sap_hieu_luc"]:
            final_context_string += (
                "\nNỘI DUNG TRÍCH DẪN CHO PHẦN LƯU Ý "
                "(trích nguyên văn vào mục LƯU Ý cuối câu trả lời, không dùng làm luật hiện hành):\n"
            )
            sap_sorted = sorted(
                context_sach["danh_sach_sap_hieu_luc"],
                key=lambda x: str(x.get("text", "")),
            )
            for idx, item in enumerate(sap_sorted, 1):
                final_context_string += f"{idx}. {item['text']}\n"

    show_van_ban_thay_the = bool(
        context_sach["lien_ket_hien_hanh"] or context_sach["danh_sach_van_ban_thay_the"]
    )
    if show_van_ban_thay_the:
        final_context_string += "\n--- VĂN BẢN THAY THẾ ---\n"
        lien_ket_hh_line = _format_lien_ket_hien_hanh(context_sach["lien_ket_hien_hanh"])
        if lien_ket_hh_line:
            final_context_string += f"{lien_ket_hh_line}\n"
        elif context_sach["danh_sach_van_ban_thay_the"]:
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

    if citation_links is not None:
        link_map = dict(citation_links)
    else:
        link_dieu_ids = _collect_dieu_ids_for_bang_link(
            can_cu_chinh_kept=can_cu_chinh_kept,
            can_cu_huong_dan_kept=can_cu_huong_dan_kept,
            can_cu_bo_tro_kept=can_cu_bo_tro_kept,
            mau_thuan_kept=context_sach["danh_sach_mau_thuan"],
            sap_hieu_luc_kept=can_cu_sap_kept,
            lien_ket_hien_hanh_kept=context_sach["lien_ket_hien_hanh"] if show_van_ban_thay_the else [],
            van_ban_thay_the_ids=(
                context_sach["danh_sach_van_ban_thay_the"] if show_van_ban_thay_the else []
            ),
        )
        link_map = _fetch_tvpl_links(link_dieu_ids)
    bang_link = _format_bang_link_trich_dan(link_map)
    if bang_link:
        final_context_string += f"\n{bang_link}"

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
    can_cu_sap_hieu_luc = [
        item.get("id")
        for item in context_tho.get("can_cu_sap_hieu_luc", [])
        if item
    ]

    return {
        "can_cu_chinh": _unique_non_empty(can_cu_chinh),
        "can_cu_huong_dan": _unique_non_empty(can_cu_huong_dan),
        "can_cu_bo_tro": _unique_non_empty(can_cu_bo_tro),
        "can_cu_mau_thuan": _unique_non_empty(can_cu_mau_thuan),
        "can_cu_sap_hieu_luc": _unique_non_empty(can_cu_sap_hieu_luc),
    }


def chuan_hoa_ket_qua_retriever(records, target_date, is_user_provide_date):
    """Trả về đồng nhất raw_ids + contexts cho mọi retriever."""
    raw_ids = {
        "can_cu_chinh": [],
        "can_cu_huong_dan": [],
        "can_cu_bo_tro": [],
        "can_cu_mau_thuan": [],
        "can_cu_sap_hieu_luc": [],
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
