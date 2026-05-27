"""Retriever V3 cho chủ đề "Chế độ tài sản của vợ chồng" — Điều 28-50 Luật HNGD 2014.

Khác với v2:
- v3 đi cùng với một KG NGỮ NGHĨA hoàn toàn mới (`docs/kg_che_do_tai_san_schema.md`,
  build bằng `scripts/build_kg_che_do_tai_san.py`).
- 8 template Cypher chuyên biệt thay vì 5 (xem `adapter/cypher_templates/tai_san/__init__.py`):
  1. phan_loai_tai_san — xác định tài sản chung/riêng (Đ33, Đ43, Đ40).
  2. nguyen_tac_che_do_tai_san — Đ29-32 áp dụng cho mọi chế độ.
  3. quyen_dinh_doat_tai_san — quyền định đoạt chung/riêng (Đ35, Đ44).
  4. dang_ky_quyen_so_huu_tai_san_chung — đăng ký GCN (Đ34).
  5. nghia_vu_tai_san — nghĩa vụ chung/riêng/liên đới (Đ27, Đ37, Đ45).
  6. chia_tai_san_thoi_ky_hon_nhan — chia trong hôn nhân (Đ38-42).
  7. thoa_thuan_che_do_tai_san — chế độ tài sản theo thỏa thuận (Đ47-50).
  8. tai_san_rieng_va_nha_o_duy_nhat — tài sản riêng + Đ31 (Đ43-46).
- Hỗ trợ bảng `COMMON_TO_LEGAL_TERMS` (term_mapping.py) làm safety-net normalizer.

Pipeline 3 bước:
    1. CLASSIFY  -> LLM chọn 1+ template name (registry topic 'tai_san').
    2. EXTRACT   -> mỗi template song song: LLM extract param (Pydantic schema)
                   + LLM extract thời điểm sự kiện.
    3. EXECUTE   -> chạy main cypher + trace cypher song song qua
                   asyncio.to_thread. Post-process bằng chuan_hoa_Context_cho_LLM.

Output: list[str], drop-in cho presentation/main.py.
"""
from __future__ import annotations

import asyncio
import json
from datetime import date
from typing import Any, List

from pydantic import BaseModel, Field

from adapter.config import driver, build_llm, RETRIEVER_LLM
from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.tai_san import TAI_SAN_REGISTRY
from adapter.cypher_templates.tai_san.term_mapping import (
    COMMON_TO_LEGAL_TERMS,
    resolve_term,
)
from utils.utils import chuan_hoa_Context_cho_LLM


# =============================================================================
# Tool description cho Router
# =============================================================================
che_do_tai_san_cua_vo_chong_v3_description = {
    "type": "function",
    "function": {
        "name": "che_do_tai_san_cua_vo_chong_v3",
        "description": (
            "Tra cứu các quy định về CHẾ ĐỘ TÀI SẢN CỦA VỢ CHỒNG (Điều 28-50 "
            "Luật Hôn nhân & Gia đình 2014). Bao gồm: phân loại tài sản chung/"
            "riêng, quyền định đoạt, đăng ký quyền sở hữu, nghĩa vụ tài sản, "
            "chia tài sản chung TRONG hôn nhân, thỏa thuận chế độ tài sản tiền "
            "hôn nhân, tài sản riêng và nhà ở duy nhất. Dùng KG ngữ nghĩa mới "
            "(8 template Cypher) để định tuyến chính xác.\n\n"
            "KHÔNG dùng cho câu hỏi 'CHIA TÀI SẢN KHI LY HÔN' (Điều 59 — đó là "
            "tool `chia_tai_san_sau_ly_hon`)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Câu hỏi cụ thể của người dùng (giữ nguyên).",
                }
            },
            "required": ["query"],
        },
    },
}


# =============================================================================
# Bước 1 — CLASSIFY (LLM picks template names from registry)
# =============================================================================
class TemplateChoice(BaseModel):
    template_name: str = Field(
        description="Tên template được chọn — phải khớp đúng 1 trong các tên đã liệt kê."
    )
    reason: str = Field(
        description="Lý do ngắn (1 câu) tại sao template này phù hợp với câu hỏi."
    )


class TemplateChoiceList(BaseModel):
    choices: List[TemplateChoice] = Field(
        description=(
            "Danh sách template phù hợp. Tối đa 3 template. Hầu hết câu hỏi "
            "chỉ cần 1; câu hỏi đa khía cạnh có thể cần 2-3."
        )
    )


def _build_classifier_prompt() -> str:
    descriptions = TAI_SAN_REGISTRY.descriptions()
    lines = [
        "Các template Cypher có sẵn cho chủ đề 'Chế độ tài sản của vợ chồng':\n"
    ]
    for name, desc in descriptions.items():
        lines.append(f"\n- **{name}**:\n{desc}\n")
    return (
        "Bạn là router chọn template Cypher để truy xuất ngữ cảnh pháp lý cho "
        "câu hỏi người dùng. Đọc câu hỏi và chọn ĐÚNG + ĐỦ template phù hợp.\n\n"
        "QUY TẮC:\n"
        "1. Đọc kỹ MỤC ĐÍCH của từng template trong danh sách bên dưới. Không chọn nhầm.\n"
        "2. Mặc định mỗi câu hỏi chỉ cần 1 template. Chỉ chọn nhiều khi câu hỏi yêu cầu "
        "rõ ràng nhiều khía cạnh (vd hỏi cả phân loại tài sản và quyền định đoạt cùng lúc).\n"
        "3. KHÔNG bịa template name ngoài danh sách.\n"
        "4. Câu hỏi 'chia tài sản KHI LY HÔN' KHÔNG thuộc danh sách này — trả về list rỗng "
        "để retriever khác xử lý.\n"
        "5. Phân biệt tinh tế:\n"
        "   - 'X là tài sản chung/riêng?' → phan_loai_tai_san (KHÔNG phải quyen_dinh_doat).\n"
        "   - 'Bán/tặng/thế chấp X có cần đồng ý?' → quyen_dinh_doat_tai_san.\n"
        "   - 'Cần cả 2 đứng tên?' / 'GCN/sổ đỏ ghi tên ai?' / 'cả 2 vợ chồng "
        "ký tên trên hợp đồng (đăng ký)?' → dang_ky_quyen_so_huu_tai_san_chung.\n"
        "   - 'Nợ là chung hay riêng?' / 'Ai trả nợ?' / 'Lấy tài sản chung "
        "trả nợ riêng?' / 'Vợ có phải trả nợ thay chồng?' → nghia_vu_tai_san "
        "(với các câu ĐỐI CHIẾU chung-riêng, set `loai_nghia_vu = 'tat_ca'` "
        "để cover đủ Đ27+30+37+45).\n"
        "   - 'Ký hợp đồng tiền hôn nhân' / 'thỏa thuận tài sản' / 'thỏa thuận "
        "về chế độ tài sản' / 'hợp đồng phân chia tài sản giữa vợ và chồng "
        "vô hiệu' (HỢP ĐỒNG PHÂN CHIA = thỏa thuận chế độ tài sản, Đ50, KHÔNG "
        "phải chia tài sản chung trong hôn nhân) → thoa_thuan_che_do_tai_san.\n"
        "   - 'Chia tài sản chung trong thời kỳ hôn nhân' (không phải ly hôn) → "
        "chia_tai_san_thoi_ky_hon_nhan.\n"
        "   - 'Nhà ở duy nhất' / 'bán nhà mua trước cưới' / 'tài sản riêng "
        "định đoạt' / 'mua nhà khi độc thân giờ bán' → "
        "tai_san_rieng_va_nha_o_duy_nhat.\n"
        + "".join(lines)
    )


async def _classify_templates(query: str) -> List[TemplateChoice]:
    llm = build_llm(model=RETRIEVER_LLM, temperature=0)
    structured_llm = llm.with_structured_output(TemplateChoiceList)

    messages = [
        {"role": "system", "content": _build_classifier_prompt()},
        {"role": "user", "content": f"Câu hỏi: {query}"},
    ]
    try:
        result: TemplateChoiceList = await structured_llm.ainvoke(messages)
    except Exception as exc:
        print(f"[Classifier-v3] Lỗi: {exc}. Fallback về phan_loai_tai_san.")
        return [TemplateChoice(template_name="phan_loai_tai_san", reason="Fallback do lỗi LLM")]

    valid_names = set(TAI_SAN_REGISTRY.names())
    valid = [c for c in result.choices if c.template_name in valid_names]
    if not valid and result.choices:
        bad = [c.template_name for c in result.choices]
        print(f"[Classifier-v3] LLM đề xuất template không hợp lệ: {bad}. Bỏ qua.")
    print(f"[Classifier-v3] Chọn: {[(c.template_name, c.reason) for c in valid]}")
    return valid


# =============================================================================
# Bước 2 — EXTRACT (mỗi template 1 LLM call extract param + 1 LLM call extract date)
# =============================================================================
class _ThoiDiem(BaseModel):
    thoi_diem_su_kien: str | None = Field(
        default=None,
        description=(
            "Mốc thời gian sự kiện trong câu hỏi định dạng 'YYYY-MM-DD'. "
            "Trả null nếu câu hỏi KHÔNG nêu mốc thời gian cụ thể."
        ),
    )


_EXTRACT_SYS_PROMPT_BASE = (
    "Bạn là chuyên gia trích xuất tham số cho câu Cypher truy xuất luật pháp. "
    "Hãy đọc câu hỏi và điền chính xác các trường vào schema `{schema_name}`.\n\n"
    "QUY TẮC QUAN TRỌNG:\n"
    "1. ĐỌC KỸ description của TỪNG field. Description chứa BẢNG MAP từ ngữ "
    "thông tục → thuật ngữ pháp lý chuẩn. BẮT BUỘC áp dụng bảng map này thay "
    "vì copy nguyên văn từ câu hỏi.\n"
    "2. Đặc biệt với các field 'asset_keyword', 'tinh_huong_keyword': KHÔNG "
    "copy nguyên văn 'đất', 'nhà', 'xe máy', 'nuôi con'... từ câu hỏi — phải "
    "MAP sang ID pháp lý chuẩn (snake_case) theo bảng trong description.\n"
    "3. Nếu trường nào không suy luận được rõ ràng, chọn giá trị mặc định an "
    "toàn (vd 'tat_ca' cho enum khia_canh/loai_*, null cho các keyword tự do).\n"
    "4. KHÔNG bịa giá trị enum ngoài Literal đã liệt kê trong schema."
)


async def _extract_template_params(
    query: str, template: CypherTemplate
) -> tuple[BaseModel, str | None]:
    """Trả về (params_pydantic_instance, target_date_str_or_None)."""
    schema_name = template.params_schema.__name__
    sys_prompt = _EXTRACT_SYS_PROMPT_BASE.format(schema_name=schema_name)
    llm = build_llm(model=RETRIEVER_LLM, temperature=0)

    params_struct_llm = llm.with_structured_output(template.params_schema)
    date_struct_llm = llm.with_structured_output(_ThoiDiem)

    params_task = params_struct_llm.ainvoke(
        [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": f"Câu hỏi: {query}"},
        ]
    )
    date_task = date_struct_llm.ainvoke(
        [
            {
                "role": "system",
                "content": (
                    "Đọc câu hỏi và xác định mốc thời gian sự kiện (nếu có). "
                    "Định dạng 'YYYY-MM-DD'. Trả null nếu không nêu."
                ),
            },
            {"role": "user", "content": f"Câu hỏi: {query}"},
        ]
    )

    params, date_obj = await asyncio.gather(params_task, date_task)

    # Safety-net: nếu LLM copy ngôn ngữ thông tục cho 'asset_keyword' /
    # 'tinh_huong_keyword' / loại_tai_san_dang_ky → resolve_term tự sửa.
    params = _normalize_with_term_mapping(params)

    # Safety-net 2: override loai_nghia_vu sang 'tat_ca' khi câu hỏi mang
    # tính đối chiếu chung-riêng (vd "tài sản chung trả nợ riêng").
    params = _override_cross_cutting_nghia_vu(params, query)

    return params, date_obj.thoi_diem_su_kien


_FIELD_TO_MAPPING: dict[str, str] = {
    "asset_keyword": "loai_tai_san",
    "tinh_huong_keyword": "loai_nghia_vu",
}


def _normalize_with_term_mapping(params: BaseModel) -> BaseModel:
    """Hậu xử lý: chuẩn hoá các field keyword theo COMMON_TO_LEGAL_TERMS."""
    data = params.model_dump()
    changed = False

    for field_name, mapping_key in _FIELD_TO_MAPPING.items():
        raw = data.get(field_name)
        if not raw:
            continue
        # Nếu raw đã là 1 legal ID đã có trong mapping values → bỏ qua.
        legal_ids = set()
        mapping = COMMON_TO_LEGAL_TERMS.get(mapping_key, {})
        for v in mapping.values():
            if isinstance(v, tuple):
                legal_ids.add(v[0])
            else:
                legal_ids.add(v)
        if raw in legal_ids:
            continue
        # Thử resolve
        resolved = resolve_term(mapping_key, raw)
        if resolved is None:
            continue
        if isinstance(resolved, tuple):
            # vd loai_nghia_vu: chỉ lấy phần loai (tuple[0])
            new_val = resolved[0]
        else:
            new_val = resolved
        if new_val != raw:
            print(
                f"[term_mapping] Field '{field_name}': '{raw}' → '{new_val}'"
            )
            data[field_name] = new_val
            changed = True

    if not changed:
        return params
    return params.__class__(**data)


def _override_cross_cutting_nghia_vu(params: BaseModel, query: str) -> BaseModel:
    """Override loai_nghia_vu='tat_ca' khi câu hỏi đối chiếu chung-riêng.

    Trường hợp điển hình (Q5): "Tài sản chung của vợ chồng có được lấy để
    trả nợ riêng không?" — LLM có xu hướng extract `loai_nghia_vu='rieng'`
    (vì có từ 'nợ riêng'), nhưng câu hỏi thực chất cần phân tích cả Đ27 +
    Đ30 + Đ37 + Đ45 (nợ riêng có thể chuyển thành nghĩa vụ chung/liên đới
    nếu phục vụ nhu cầu thiết yếu gia đình). Lúc đó dùng `tat_ca` để
    template tự whitelist đủ 4 Điều cốt lõi.
    """
    data = params.model_dump()
    if "loai_nghia_vu" not in data:
        return params
    current = data.get("loai_nghia_vu")
    if current == "tat_ca":
        return params

    q_norm = query.lower()
    has_chung = ("tài sản chung" in q_norm) or ("nợ chung" in q_norm) or (
        "nghĩa vụ chung" in q_norm
    )
    has_rieng = ("tài sản riêng" in q_norm) or ("nợ riêng" in q_norm) or (
        "nghĩa vụ riêng" in q_norm
    )

    # Pattern điển hình: "X chung trả/đóng/thanh toán Y riêng" (hoặc đảo lại)
    cross_patterns = [
        ("tài sản chung", "nợ riêng"),
        ("tài sản chung", "nghĩa vụ riêng"),
        ("tài sản riêng", "nợ chung"),
        ("tài sản riêng", "nghĩa vụ chung"),
        ("nợ chung", "tài sản riêng"),
        ("nợ riêng", "tài sản chung"),
    ]
    is_cross = any(a in q_norm and b in q_norm for a, b in cross_patterns)

    # Pattern phụ: hỏi "nợ chung hay riêng", "phân biệt chung và riêng"...
    distinguishing_phrases = [
        "chung hay riêng",
        "riêng hay chung",
        "phân biệt nghĩa vụ chung và riêng",
        "phân biệt nợ chung và riêng",
        "khi nào nợ riêng thành chung",
        "khi nào nợ của một bên",
        "vợ có phải trả nợ thay chồng",
        "chồng có phải trả nợ thay vợ",
        "trả nợ thay",
    ]
    has_distinguish = any(p in q_norm for p in distinguishing_phrases)

    should_override = is_cross or has_distinguish or (has_chung and has_rieng)
    if not should_override:
        return params

    print(
        f"[cross-cutting override] loai_nghia_vu: '{current}' → 'tat_ca' "
        f"(query có đối chiếu chung-riêng)"
    )
    data["loai_nghia_vu"] = "tat_ca"
    # Khi đối chiếu, KHÔNG khoá tinh_huong_keyword nữa để expand đầy đủ.
    if "tinh_huong_keyword" in data:
        data["tinh_huong_keyword"] = None
    try:
        return params.__class__(**data)
    except Exception as exc:
        print(f"[cross-cutting override] failed: {exc}")
        return params


# =============================================================================
# Bước 3 — EXECUTE
# =============================================================================
def _today_str() -> str:
    return date.today().strftime("%Y-%m-%d")


def _run_template_sync(
    template: CypherTemplate, params: BaseModel, target_date: str
) -> dict[str, Any] | None:
    runtime_params = template.build_params(params)
    runtime_params["target_date"] = target_date
    print(f"[Template:{template.name}] params={runtime_params}")
    try:
        records, _, _ = driver.execute_query(template.cypher, **runtime_params)
    except Exception as exc:
        print(f"[Template:{template.name}] Cypher error: {exc}")
        return None
    if not records:
        print(f"[Template:{template.name}] Không có record nào.")
        return None
    return records[0].data()


def _run_trace_sync(
    template: CypherTemplate, params: BaseModel, target_date: str
) -> list[dict[str, Any]]:
    """Chạy trace cypher → list các triple (sn)-[rel]->(luat)."""
    if template.trace_cypher is None:
        return []
    runtime_params = template.build_params(params)
    runtime_params["target_date"] = target_date
    try:
        records, _, _ = driver.execute_query(template.trace_cypher, **runtime_params)
    except Exception as exc:
        print(f"[Template:{template.name}] Trace cypher error: {exc}")
        return []
    if not records:
        return []
    raw = records[0].data().get("seed_trace") or []
    return [t for t in raw if t]


def _format_trace(trace: list[dict[str, Any]]) -> str:
    """Render trace thành chuỗi (node:Label "id") -[REL]-> (node:Label "id")."""
    if not trace:
        return "  (rỗng — không match được node ngữ nghĩa nào)"
    lines = []
    for t in trace:
        src = f'({t.get("src_label", "?")} "{t.get("src_id", "?")}")'
        dst = f'({t.get("dst_label", "?")} "{t.get("dst_id", "?")}")'
        rel = t.get("rel", "?")
        lines.append(f"  • {src} -[{rel}]-> {dst}")
    return "\n".join(lines)


def _format_template_output(
    template: CypherTemplate,
    params: BaseModel,
    target_date: str,
    trace: list[dict[str, Any]],
    normalized_context: str | None,
    error_msg: str | None = None,
) -> str:
    lines = [
        "--- CONTEXT TỪ GRAPH ---",
        "",
        " PARAMS",
        f"  {template.build_params(params)} | target_date={target_date}",
        "",
        " DEBUG TRACE — Semantic Seed → LegalProvision (CAN_CU_TAI)",
        _format_trace(trace),
        "",
    ]
    if error_msg:
        lines.append(f"⚠ {error_msg}")
    elif normalized_context:
        lines.append(normalized_context.rstrip())
    else:
        lines.append("⚠ Không có context (cypher trả 0 record).")
    return "\n".join(lines)


# =============================================================================
# Public entrypoint cho tool router
# =============================================================================
async def che_do_tai_san_cua_vo_chong_v3(query: str) -> List[str]:
    """3 bước: classify → extract → execute → normalize.

    Trả về list[str] (mỗi string là context đã chuẩn hoá cho LLM downstream),
    drop-in cho presentation/main.py.
    """
    print(f"[Agent che_do_tai_san_cua_vo_chong_v3] Đang xử lý: '{query}'...")

    choices = await _classify_templates(query)
    if not choices:
        return [
            "Câu hỏi này không thuộc phạm vi 'Chế độ tài sản của vợ chồng' "
            "(có thể thuộc 'chia tài sản khi ly hôn' — hãy gọi retriever tương ứng)."
        ]

    # --- Bước 2: extract param song song -------------------------------------
    templates: List[CypherTemplate] = []
    extract_tasks = []
    for choice in choices:
        template = TAI_SAN_REGISTRY.get(choice.template_name)
        templates.append(template)
        extract_tasks.append(_extract_template_params(query, template))

    extracted: List[tuple[BaseModel, str | None]] = await asyncio.gather(*extract_tasks)

    user_dates = [d for _, d in extracted if d]
    is_user_provide_date = bool(user_dates)
    target_date = user_dates[0] if user_dates else _today_str()

    # --- Bước 3: chạy main + trace song song ---------------------------------
    run_tasks = []
    for template, (params, _) in zip(templates, extracted):
        run_tasks.append(
            asyncio.to_thread(_run_template_sync, template, params, target_date)
        )
        run_tasks.append(
            asyncio.to_thread(_run_trace_sync, template, params, target_date)
        )
    flat = await asyncio.gather(*run_tasks)
    pairs = [(flat[i], flat[i + 1]) for i in range(0, len(flat), 2)]

    contexts: List[str] = []
    for template, (params, _), (record, trace) in zip(templates, extracted, pairs):
        normalized: str | None = None
        error_msg: str | None = None
        if record is None or "Context_Tho" not in record:
            error_msg = "Không tìm thấy căn cứ phù hợp trong KG (main cypher trả 0 record)."
        else:
            try:
                normalized = chuan_hoa_Context_cho_LLM(
                    record, target_date, is_user_provide_date
                )
            except Exception as exc:
                print(f"[Template:{template.name}] Normalize error: {exc}")
                error_msg = (
                    f"Lỗi chuẩn hoá: {exc}\n"
                    f"Raw (truncated): "
                    f"{json.dumps(record, ensure_ascii=False, default=str)[:500]}..."
                )
        contexts.append(
            _format_template_output(
                template=template,
                params=params,
                target_date=target_date,
                trace=trace,
                normalized_context=normalized,
                error_msg=error_msg,
            )
        )

    return contexts
