"""Retriever cho chủ đề "Cấp dưỡng" — Điều 107-120, Đ82 K2 Luật HNGD 2014.

Pipeline 3 bước:
    1. CLASSIFY  -> LLM chọn 1+ template (registry topic 'cap_duong').
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
from adapter.cypher_templates.cap_duong import CAP_DUONG_REGISTRY
from adapter.cypher_templates.cap_duong.term_mapping import resolve_term
from adapter.graph_viz import save_lazy_viz_stub
from application.legal_context import encode_context_record


cap_duong_description = {
    "type": "function",
    "function": {
        "name": "cap_duong",
        "description": (
            "Tra cứu quy định về cấp dưỡng theo Điều 107–119: nghĩa vụ cấp dưỡng, "
            "trốn/chây ì cấp dưỡng, buộc thực hiện nghĩa vụ, chấm dứt cấp dưỡng, "
            "mức và phương thức cấp dưỡng, quyền yêu cầu Tòa án thực hiện cấp dưỡng."
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


class TemplateChoice(BaseModel):
    template_name: str = Field(
        description="Tên template — phải khớp 1 trong 6 template đã liệt kê."
    )
    reason: str = Field(description="Lý do ngắn (1 câu) chọn template này.")


class TemplateChoiceList(BaseModel):
    choices: List[TemplateChoice] = Field(
        description="Danh sách template phù hợp. Tối đa 3. Hầu hết câu chỉ cần 1."
    )


def _build_classifier_prompt() -> str:
    descriptions = CAP_DUONG_REGISTRY.descriptions()
    lines = ["Các template Cypher cho chủ đề 'Cấp dưỡng':\n"]
    for name, desc in descriptions.items():
        lines.append(f"\n- **{name}**:\n{desc}\n")
    return (
        "Bạn là router chọn template Cypher để truy xuất ngữ cảnh pháp lý cho "
        "câu hỏi về CẤP DƯỠNG theo Luật Hôn nhân và Gia đình 2014.\n\n"
        "QUY TẮC ƯU TIÊN (theo thứ tự):\n"
        "1. Có 'chấm dứt', 'hết nghĩa vụ', 'khi nào không phải cấp dưỡng', "
        "'một bên chết', 'tái hôn' → cham_dut_nghia_vu_cap_duong.\n"
        "2. Có 'ai có quyền yêu cầu', 'khởi kiện', 'Tòa án buộc', "
        "'không chịu', 'trốn tránh' → quyen_yeu_cau_va_cuong_che_cap_duong.\n"
        "3. Có 'mức', 'bao nhiêu', 'tối thiểu', số tiền cụ thể, "
        "'giảm/tăng mức' → muc_va_phan_bo_cap_duong.\n"
        "4. Có 'phương thức', 'hằng tháng/quý/năm', 'một lần', "
        "'tạm ngừng', 'đổi cách trả' → phuong_thuc_va_tam_ngung_cap_duong.\n"
        "5. Có 'người không trực tiếp nuôi con', 'thay đổi người trực tiếp nuôi', "
        "'không yêu cầu nhận cấp dưỡng', hoặc hỏi riêng nghĩa vụ cấp dưỡng cho con "
        "sau ly hôn → cap_duong_cho_con_sau_ly_hon.\n"
        "6. Có quan hệ gia đình cụ thể, con ngoài giá thú, không đăng ký kết hôn, "
        "độ tuổi, vợ/chồng cũ → nghia_vu_cap_duong_theo_quan_he.\n"
        "7. 'Mức cấp dưỡng hằng tháng' vẫn chọn muc_va_phan_bo_cap_duong.\n"
        "8. 'Cấp dưỡng đến bao nhiêu tuổi' chọn nghia_vu_cap_duong_theo_quan_he, "
        "KHÔNG chọn chấm dứt.\n"
        "9. 'Khó khăn kinh tế' + xin tạm dừng → phương thức; + xin giảm số tiền "
        "→ mức; hỏi cả hai có thể chọn cả hai.\n"
        "10. 'Tài sản riêng có phải dùng cấp dưỡng vợ cũ' → quan hệ vợ chồng sau "
        "ly hôn; hỏi thêm số tiền có thể thêm template mức.\n"
        "11. Mặc định 1 template/câu; tối đa 3 khi có nhiều yêu cầu độc lập.\n"
        "12. KHÔNG bịa template name ngoài danh sách.\n"
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
        print(f"[Classifier-cap_duong] Lỗi: {exc}. Fallback quan hệ.")
        return [
            TemplateChoice(
                template_name="nghia_vu_cap_duong_theo_quan_he",
                reason="Fallback do lỗi LLM",
            )
        ]

    valid_names = set(CAP_DUONG_REGISTRY.names())
    valid = [c for c in result.choices if c.template_name in valid_names]
    if not valid and result.choices:
        bad = [c.template_name for c in result.choices]
        print(f"[Classifier-cap_duong] Template không hợp lệ: {bad}. Fallback.")
        valid = [
            TemplateChoice(
                template_name="nghia_vu_cap_duong_theo_quan_he",
                reason="Fallback template không hợp lệ",
            )
        ]
    if not valid:
        valid = [
            TemplateChoice(
                template_name="nghia_vu_cap_duong_theo_quan_he",
                reason="Fallback mặc định",
            )
        ]
    print(f"[Classifier-cap_duong] Chọn: {[(c.template_name, c.reason) for c in valid]}")
    return valid[:3]


_EXTRACT_SYS_PROMPT_BASE = (
    "Bạn là chuyên gia trích xuất tham số cho câu Cypher truy xuất luật pháp "
    "về cấp dưỡng. Điền chính xác các trường schema `{schema_name}`.\n\n"
    "QUY TẮC:\n"
    "1. ĐỌC description từng field — có bảng map ngữ thông tục → enum chuẩn.\n"
    "2. Không suy luận được → chọn giá trị mặc định an toàn (khong_ro, tong_quat).\n"
    "3. KHÔNG bịa enum ngoài Literal.\n"
    "4. `thoi_diem_su_kien`: mốc thời gian sự kiện 'YYYY-MM-DD' hoặc null nếu "
    "câu hỏi không nêu ngày/tháng/năm cụ thể."
)

_ENUM_FIELDS = {
    "quan_he",
    "tinh_trang_nguoi_duoc_cap_duong",
    "boi_canh",
    "khia_canh",
    "khia_canh_muc",
    "chu_ky",
    "chu_ky_duoc_hoi",
    "ly_do_cham_dut",
    "nguoi_yeu_cau",
    "tinh_trang_thuc_hien",
    "doi_tuong_nhan",
    "doi_tuong_duoc_cap_duong",
    "kho_khan_kinh_te",
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
    return {
        k: v
        for k, v in runtime_params.items()
        if "whitelist" not in k.lower()
    }


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


async def cap_duong(query: str) -> dict[str, Any]:
    """Truy xuất căn cứ cấp dưỡng bằng các template ngữ nghĩa phù hợp.

    Args:
        query: Câu hỏi pháp lý đã được Router giải nghĩa đầy đủ ngữ cảnh.

    Returns:
        Dictionary gồm ``contexts`` là danh sách LegalContextBundle đã encode,
        ``debug`` mô tả template/params, và ``graph_viz_id`` nếu tạo được
        snapshot visualize. Lỗi từng template được giữ dưới dạng context text
        để pipeline tổng hợp vẫn có thể phản hồi an toàn.
    """
    print(f"[Agent cap_duong] Đang xử lý: '{query}'...")

    choices = await _classify_templates(query)

    templates: List[CypherTemplate] = []
    extract_tasks = []
    for choice in choices:
        template = CAP_DUONG_REGISTRY.get(choice.template_name)
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
                    retriever_name="cap_duong",
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
                "topic": "cap_duong",
                "template": template.name,
                "params": runtime_params,
                "context_tho": context_tho,
            }
        )

    if lazy_sources:
        graph_viz_id = save_lazy_viz_stub(lazy_sources, query=query, target_date=target_date)

    result: dict[str, Any] = {
        "contexts": contexts,
        "debug": "\n\n".join(debug_parts),
    }
    if graph_viz_id:
        result["graph_viz_id"] = graph_viz_id
    return result
