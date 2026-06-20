"""Retriever cho chủ đề "Chung sống như vợ chồng không đăng ký" — Đ5, Đ14-16 Luật HNGD 2014.

Pipeline 3 bước:
    1. CLASSIFY  -> LLM chọn 1+ template (registry topic 'chung_song_nhu_vo_chong').
    2. EXTRACT   -> 1 LLM call mỗi template (params + thời điểm sự kiện).
    3. EXECUTE   -> chạy Cypher và encode ``LegalContextBundle``.

Output: dict ``{"contexts": list[str], "debug": str}``.
"""
from __future__ import annotations

import asyncio
import json
from datetime import date
from typing import Any, List

from pydantic import BaseModel, Field

from adapter.config import driver, build_llm, RETRIEVER_LLM
from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.extract_schema import (
    build_params_with_date_schema,
    split_params_and_date,
)
from adapter.cypher_templates.chung_song_nhu_vo_chong import (
    CHUNG_SONG_NHU_VO_CHONG_REGISTRY,
)
from adapter.cypher_templates.chung_song_nhu_vo_chong.term_mapping import resolve_term
from adapter.graph_viz import save_lazy_viz_stub
from application.legal_context import encode_context_record


chung_song_nhu_vo_chong_description = {
    "type": "function",
    "function": {
        "name": "chung_song_nhu_vo_chong",
        "description": (
            "Lấy thông tin quy định về giải quyết hậu quả; xác định quyền, nghĩa vụ "
            "của cha mẹ và con; giải quyết quan hệ tài sản, nghĩa vụ và hợp đồng "
            "trong trường hợp nam, nữ chung sống với nhau như vợ chồng mà không "
            "đăng ký kết hôn."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Câu hỏi cụ thể của người dùng.",
                }
            },
            "required": ["query"],
        },
    },
}


class TemplateChoice(BaseModel):
    template_name: str = Field(
        description="Tên template — phải khớp 1 trong 6 template đã liệt kê."
    )
    reason: str = Field(description="Lý do ngắn (1 câu) chọn template này.")


class TemplateChoiceList(BaseModel):
    choices: List[TemplateChoice] = Field(
        description="Danh sách template phù hợp. Tối đa 2. Hầu hết câu chỉ cần 1."
    )


def _build_classifier_prompt() -> str:
    descriptions = CHUNG_SONG_NHU_VO_CHONG_REGISTRY.descriptions()
    lines = [
        "Các template Cypher cho chủ đề 'Chung sống như vợ chồng không đăng ký':\n"
    ]
    for name, desc in descriptions.items():
        lines.append(f"\n- **{name}**:\n{desc}\n")
    return (
        "Bạn là router chọn template Cypher để truy xuất ngữ cảnh pháp lý cho "
        "câu hỏi về CHUNG SỐNG NHƯ VỢ CHỒNG KHÔNG ĐĂNG KÝ KẾT HÔN "
        "(Điều 5, 14-16 Luật HNGD 2014).\n\n"
        "QUY TẮC ƯU TIÊN (theo thứ tự):\n"
        "1. Có 'đang có vợ/chồng', 'đã có gia đình', 'chưa ly hôn', 'vi phạm', "
        "'bị cấm' -> xac_dinh_tinh_hop_phap_chung_song.\n"
        "2. Có 'con', 'nuôi con', 'chăm sóc', 'cấp dưỡng', 'quyền cha/mẹ/con' "
        "-> quyen_nghia_vu_cha_me_con.\n"
        "3. Có 'bao lâu phải cưới/kết hôn', 'đăng ký sau', 'hôn nhân tính từ khi nào' "
        "-> dang_ky_ket_hon_sau_chung_song.\n"
        "4. Có 'chia tài sản', 'tài sản lúc sống thử', 'công sức nội trợ', "
        "'quyền lợi phụ nữ và con khi chia' -> giai_quyet_tai_san_khi_chung_song.\n"
        "5. Có 'nợ', 'nghĩa vụ', 'ai trả', 'hợp đồng', 'giao dịch' và không phải "
        "chia tài sản -> giai_quyet_nghia_vu_va_hop_dong.\n"
        "6. Có 'hậu quả', 'giải quyết thế nào', 'có được coi là vợ chồng không' "
        "mà không có nhánh cụ thể hơn -> hau_qua_phap_ly_chung_song.\n"
        "7. 'Bạn trai/bạn gái' không đủ để suy ra độc thân hay đã có vợ/chồng.\n"
        "8. Ranh giới: đã đăng ký kết hôn + tài sản hôn nhân -> che_do_tai_san; "
        "thủ tục đăng ký -> dang_ky_ket_hon; nuôi con sau ly hôn -> cha_me_con_sau_ly_hon.\n"
        "9. Mặc định 1 template/câu; tối đa 2 khi có hai yêu cầu độc lập.\n"
        "10. KHÔNG bịa template name ngoài danh sách.\n"
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
        print(f"[Classifier-chung_song] Lỗi: {exc}. Fallback hậu quả.")
        return [
            TemplateChoice(
                template_name="hau_qua_phap_ly_chung_song",
                reason="Fallback do lỗi LLM",
            )
        ]

    valid_names = set(CHUNG_SONG_NHU_VO_CHONG_REGISTRY.names())
    valid = [c for c in result.choices if c.template_name in valid_names]
    if not valid and result.choices:
        bad = [c.template_name for c in result.choices]
        print(f"[Classifier-chung_song] Template không hợp lệ: {bad}. Fallback.")
        valid = [
            TemplateChoice(
                template_name="hau_qua_phap_ly_chung_song",
                reason="Fallback template không hợp lệ",
            )
        ]
    if not valid:
        valid = [
            TemplateChoice(
                template_name="hau_qua_phap_ly_chung_song",
                reason="Fallback mặc định",
            )
        ]
    print(f"[Classifier-chung_song] Chọn: {[(c.template_name, c.reason) for c in valid]}")
    return valid[:2]


_EXTRACT_SYS_PROMPT_BASE = (
    "Bạn là chuyên gia trích xuất tham số cho câu Cypher truy xuất luật pháp "
    "về chung sống như vợ chồng không đăng ký kết hôn. "
    "Điền chính xác các trường schema `{schema_name}`.\n\n"
    "QUY TẮC:\n"
    "1. ĐỌC description từng field — có bảng map ngữ thông tục → enum chuẩn.\n"
    "2. Không suy luận được → chọn giá trị mặc định an toàn (khong_ro, tong_quat).\n"
    "3. KHÔNG bịa enum ngoài Literal.\n"
    "4. `thoi_diem_su_kien`: mốc thời gian sự kiện 'YYYY-MM-DD' hoặc null nếu "
    "câu hỏi không nêu ngày/tháng/năm cụ thể."
)

_ENUM_FIELDS = {
    "tinh_trang_hon_nhan_cac_ben",
    "khia_canh_hop_phap",
    "khia_canh_hau_qua",
    "tinh_trang_dang_ky",
    "khia_canh_thoi_diem",
    "khia_canh_con",
    "chu_the_quan_tam",
    "co_thoa_thuan",
    "khia_canh_tai_san",
    "loai_quan_he",
}


def _normalize_with_term_mapping(params: BaseModel, query: str) -> BaseModel:
    data = params.model_dump()
    changed = False

    for field_name in _ENUM_FIELDS:
        if field_name not in data:
            continue
        current = data.get(field_name)
        if current and current not in ("khong_ro", "chua_ro", "tat_ca", "tong_quat"):
            continue
        resolved = resolve_term(field_name, query)
        if resolved and resolved != current:
            print(f"[term_mapping] {field_name}: '{current}' → '{resolved}'")
            data[field_name] = resolved
            changed = True

    if not changed:
        return params
    try:
        return params.__class__(**data)
    except Exception as exc:
        print(f"[term_mapping] rebuild failed: {exc}")
        return params


async def _extract_template_params(
    query: str, template: CypherTemplate
) -> tuple[BaseModel, str | None]:
    combined_schema = build_params_with_date_schema(template.params_schema)
    schema_name = combined_schema.__name__
    sys_prompt = _EXTRACT_SYS_PROMPT_BASE.format(schema_name=schema_name)
    llm = build_llm(model=RETRIEVER_LLM, temperature=0)
    struct_llm = llm.with_structured_output(combined_schema)

    raw = await struct_llm.ainvoke(
        [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": f"Câu hỏi: {query}"},
        ]
    )
    params, thoi_diem = split_params_and_date(raw, template.params_schema)
    params = _normalize_with_term_mapping(params, query)
    return params, thoi_diem


def _today_str() -> str:
    return date.today().strftime("%Y-%m-%d")


def _run_template_sync(
    template: CypherTemplate, params: BaseModel, target_date: str
) -> dict[str, Any] | None:
    runtime_params = template.build_params(params)
    runtime_params["target_date"] = target_date
    runtime_params["query_date"] = _today_str()
    print(f"[Template:{template.name}] params={runtime_params}")
    try:
        records, _, _ = driver.execute_query(template.cypher, **runtime_params)
    except Exception as exc:
        print(f"[Template:{template.name}] Cypher error: {exc}")
        return None
    if not records:
        print(f"[Template:{template.name}] Không có record.")
        return None
    return records[0].data()


def _params_for_display(runtime_params: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in runtime_params.items() if "whitelist" not in k.lower()}


def _format_retrieval_debug(
    template_name: str, reason: str, runtime_params: dict[str, Any]
) -> str:
    return "\n".join(
        [
            f"Template: {template_name}",
            f"Lý do: {reason}",
            f"Params: {_params_for_display(runtime_params)}",
        ]
    )


async def chung_song_nhu_vo_chong(query: str) -> dict[str, Any]:
    """Truy xuất căn cứ về chung sống như vợ chồng không đăng ký.

    Args:
        query: Câu hỏi pháp lý đã được Router giải nghĩa đầy đủ ngữ cảnh.

    Returns:
        Dictionary gồm các LegalContextBundle trong ``contexts``, thông tin
        chẩn đoán trong ``debug`` và ``graph_viz_id`` tùy chọn. Context lỗi
        vẫn được trả dưới dạng text để không làm hỏng toàn bộ lượt hỏi.
    """
    print(f"[Agent chung_song_nhu_vo_chong] Đang xử lý: '{query}'...")

    choices = await _classify_templates(query)

    templates: List[CypherTemplate] = []
    extract_tasks = []
    for choice in choices:
        template = CHUNG_SONG_NHU_VO_CHONG_REGISTRY.get(choice.template_name)
        templates.append(template)
        extract_tasks.append(_extract_template_params(query, template))

    extracted: List[tuple[BaseModel, str | None]] = await asyncio.gather(*extract_tasks)

    user_dates = [d for _, d in extracted if d]
    is_user_provide_date = bool(user_dates)
    target_date = user_dates[0] if user_dates else _today_str()

    records = await asyncio.gather(
        *(
            asyncio.to_thread(_run_template_sync, template, params, target_date)
            for template, (params, _) in zip(templates, extracted)
        )
    )

    contexts: List[str] = []
    debug_parts: List[str] = []
    for template, choice, (params, _), record in zip(
        templates, choices, extracted, records
    ):
        runtime_params = template.build_params(params)
        runtime_params["target_date"] = target_date
        runtime_params["query_date"] = _today_str()
        debug_text = _format_retrieval_debug(
            template_name=template.name,
            reason=choice.reason,
            runtime_params=runtime_params,
        )
        debug_parts.append(debug_text)
        print(f"[Retriever debug]\n{debug_text}\n")

        if record is None or "Context_Tho" not in record:
            contexts.append(
                "Không tìm thấy căn cứ phù hợp trong KG (main cypher trả 0 record)."
            )
            continue

        try:
            contexts.append(
                encode_context_record(
                    record,
                    target_date,
                    is_user_provide_date,
                    retriever_name="chung_song_nhu_vo_chong",
                    template_name=template.name,
                )
            )
        except Exception as exc:
            print(f"[Template:{template.name}] Normalize error: {exc}")
            contexts.append(
                f"Lỗi chuẩn hoá: {exc}\n"
                f"Raw: {json.dumps(record, ensure_ascii=False, default=str)[:500]}..."
            )

    graph_viz_id = None
    lazy_sources: list[dict[str, Any]] = []
    for template, (params, _), record in zip(templates, extracted, records):
        if record is None or "Context_Tho" not in record:
            continue
        context_tho = record.get("Context_Tho")
        if not context_tho:
            continue
        runtime_params = template.build_params(params)
        runtime_params["target_date"] = target_date
        runtime_params["query_date"] = _today_str()
        lazy_sources.append(
            {
                "topic": "chung_song_nhu_vo_chong",
                "template": template.name,
                "params": runtime_params,
                "context_tho": context_tho,
            }
        )

    if lazy_sources:
        graph_viz_id = save_lazy_viz_stub(
            lazy_sources, query=query, target_date=target_date
        )

    result: dict[str, Any] = {
        "contexts": contexts,
        "debug": "\n\n".join(debug_parts),
    }
    if graph_viz_id:
        result["graph_viz_id"] = graph_viz_id
    return result
