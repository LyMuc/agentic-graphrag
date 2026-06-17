"""Retriever cho chủ đề "Quy định chung ly hôn" — Điều 51-57 Luật HNGD 2014.

Pipeline 3 bước:
    1. CLASSIFY  -> LLM chọn 1+ template (registry topic 'quy_dinh_chung_ly_hon').
    2. EXTRACT   -> 1 LLM call mỗi template (params + thời điểm sự kiện).
    3. EXECUTE   -> chạy Cypher qua asyncio.to_thread → chuan_hoa_Context_cho_LLM.

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
from adapter.cypher_templates.quy_dinh_chung_ly_hon import QUY_DINH_CHUNG_LY_HON_REGISTRY
from adapter.cypher_templates.quy_dinh_chung_ly_hon.term_mapping import resolve_term
from adapter.graph_viz import save_lazy_viz_stub
from utils.utils import chuan_hoa_Context_cho_LLM


quy_dinh_chung_ly_hon_description = {
    "type": "function",
    "function": {
        "name": "quy_dinh_chung_ly_hon",
        "description": (
            "Tra cứu các quy định chung về ly hôn bao gồm: quyền yêu cầu giải quyết "
            "ly hôn, thụ lý đơn, thuận tình ly hôn, ly hôn theo yêu cầu một bên "
            "(đơn phương ly hôn) và thời điểm chấm dứt hôn nhân. "
            "Không dùng cho các câu hỏi liên quan đến tài sản, tiền vay, nợ sau ly hôn."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Câu hỏi cụ thể của người dùng về việc ly hôn, quyền ly hôn "
                        "hoặc thủ tục ly hôn."
                    ),
                }
            },
            "required": ["query"],
        },
    },
}


class TemplateChoice(BaseModel):
    template_name: str = Field(
        description="Tên template — phải khớp 1 trong 7 template đã liệt kê."
    )
    reason: str = Field(description="Lý do ngắn (1 câu) chọn template này.")


class TemplateChoiceList(BaseModel):
    choices: List[TemplateChoice] = Field(
        description="Danh sách template phù hợp. Tối đa 3. Hầu hết câu chỉ cần 1."
    )


def _build_classifier_prompt() -> str:
    descriptions = QUY_DINH_CHUNG_LY_HON_REGISTRY.descriptions()
    lines = ["Các template Cypher cho chủ đề 'Quy định chung ly hôn':\n"]
    for name, desc in descriptions.items():
        lines.append(f"\n- **{name}**:\n{desc}\n")
    return (
        "Bạn là router chọn template Cypher để truy xuất ngữ cảnh pháp lý cho "
        "câu hỏi về QUY ĐỊNH CHUNG LY HÔN theo Luật Hôn nhân và Gia đình 2014.\n\n"
        "QUY TẮC ƯU TIÊN (theo thứ tự):\n"
        "1. Có 'mất tích', 'biệt tích', 'không liên lạc được', 'đã tuyên bố mất tích' "
        "→ ly_hon_khi_mat_tich_hoac_khong_lien_lac.\n"
        "2. Có 'mang thai', 'mới sinh', 'nuôi con dưới 12 tháng', 'ai có quyền yêu cầu', "
        "'cha mẹ/người thân yêu cầu', 'bệnh tâm thần kèm bạo lực' "
        "→ quyen_yeu_cau_va_han_che_ly_hon.\n"
        "3. Có 'hòa giải', 'thụ lý', 'đã nộp đơn nhưng Tòa chưa giải quyết' "
        "→ hoa_giai_va_thu_ly_ly_hon.\n"
        "4. Có 'thuận tình' và hỏi khái niệm, điều kiện, khi nào Tòa công nhận "
        "→ dieu_kien_thuan_tinh_ly_hon.\n"
        "5. So sánh thuận tình với đơn phương, một bên không đồng ý, điều kiện tiến hành "
        "nói chung hoặc ai đứng tên đơn → xac_dinh_hinh_thuc_ly_hon.\n"
        "6. Có 'đơn phương' kèm ngoại tình, bạo lực, cờ bạc, rượu chè, bỏ mặc, "
        "mâu thuẫn trầm trọng, ly thân → can_cu_don_phuong_ly_hon.\n"
        "7. Có 'khi nào chấm dứt hôn nhân', 'đang làm thủ tục', 'ly thân có chấm dứt', "
        "'xé giấy kết hôn', 'chung sống với người khác khi chờ ly hôn' "
        "→ thoi_diem_cham_dut_hon_nhan.\n"
        "8. 'Vợ mới sinh có được yêu cầu ly hôn không' → quyen_yeu_cau_va_han_che_ly_hon "
        "(hạn chế chỉ áp dụng cho chồng).\n"
        "9. 'Ngoại tình có được ly hôn không' → can_cu_don_phuong_ly_hon.\n"
        "10. 'Không liên lạc được' KHÔNG mặc định map thành đã tuyên bố mất tích.\n"
        "11. 'Thuận tình có phải hòa giải không' → hoa_giai_va_thu_ly_ly_hon.\n"
        "12. 'Điều kiện để ly hôn' không nêu rõ hình thức → xac_dinh_hinh_thuc_ly_hon.\n"
        "13. Ranh giới: chia tài sản/cấp dưỡng/giao con chi tiết → topic khác; "
        "thẩm quyền Tòa/thời hạn tố tụng → topic tố tụng.\n"
        "14. Mặc định 1 template/câu; tối đa 3 khi có nhiều yêu cầu độc lập.\n"
        "15. KHÔNG bịa template name ngoài danh sách.\n"
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
        print(f"[Classifier-quy_dinh_chung_ly_hon] Lỗi: {exc}. Fallback quyền.")
        return [
            TemplateChoice(
                template_name="quyen_yeu_cau_va_han_che_ly_hon",
                reason="Fallback do lỗi LLM",
            )
        ]

    valid_names = set(QUY_DINH_CHUNG_LY_HON_REGISTRY.names())
    valid = [c for c in result.choices if c.template_name in valid_names]
    if not valid and result.choices:
        bad = [c.template_name for c in result.choices]
        print(
            f"[Classifier-quy_dinh_chung_ly_hon] Template không hợp lệ: {bad}. Fallback."
        )
        valid = [
            TemplateChoice(
                template_name="quyen_yeu_cau_va_han_che_ly_hon",
                reason="Fallback template không hợp lệ",
            )
        ]
    if not valid:
        valid = [
            TemplateChoice(
                template_name="quyen_yeu_cau_va_han_che_ly_hon",
                reason="Fallback mặc định",
            )
        ]
    print(
        f"[Classifier-quy_dinh_chung_ly_hon] Chọn: "
        f"{[(c.template_name, c.reason) for c in valid]}"
    )
    return valid[:3]


_EXTRACT_SYS_PROMPT_BASE = (
    "Bạn là chuyên gia trích xuất tham số cho câu Cypher truy xuất luật pháp "
    "về quy định chung ly hôn. Điền chính xác các trường schema `{schema_name}`.\n\n"
    "QUY TẮC:\n"
    "1. ĐỌC description từng field — có bảng map ngữ thông tục → enum chuẩn.\n"
    "2. Không suy luận được → chọn giá trị mặc định an toàn (khong_ro, tong_quat).\n"
    "3. KHÔNG bịa enum ngoài Literal.\n"
    "4. `thoi_diem_su_kien`: mốc thời gian sự kiện 'YYYY-MM-DD' hoặc null nếu "
    "câu hỏi không nêu ngày/tháng/năm cụ thể."
)

_ENUM_FIELDS = {
    "chu_the_yeu_cau",
    "tinh_trang_vo_con",
    "nang_luc_va_bao_luc",
    "boi_canh_yeu_cau",
    "khia_canh_quyen",
    "giai_doan",
    "hinh_thuc_ly_hon",
    "dang_ky_ket_hon",
    "khia_canh_hoa_giai",
    "muc_do_thoa_thuan",
    "noi_dung_thoa_thuan",
    "tu_nguyen",
    "khia_canh_thuan_tinh",
    "y_chi_vo_chong",
    "khia_canh_hinh_thuc",
    "co_con_duoi_12_thang",
    "co_tranh_chap_tai_san_con",
    "boi_canh_to_tung",
    "can_cu",
    "chu_the_don_phuong",
    "hau_qua_hon_nhan",
    "hoa_giai_tai_toa",
    "boi_canh_hon_nhan",
    "tinh_trang",
    "da_thong_bao_tim_kiem",
    "khia_canh_mat_tich",
    "chu_the_vang_mat",
    "tinh_huong",
    "khia_canh_cham_dut",
    "hanh_vi_trong_khi_cho",
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


async def quy_dinh_chung_ly_hon(query: str) -> dict[str, Any]:
    """3 bước: classify → extract → execute → normalize."""
    print(f"[Agent quy_dinh_chung_ly_hon] Đang xử lý: '{query}'...")

    choices = await _classify_templates(query)

    templates: List[CypherTemplate] = []
    extract_tasks = []
    for choice in choices:
        template = QUY_DINH_CHUNG_LY_HON_REGISTRY.get(choice.template_name)
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
                chuan_hoa_Context_cho_LLM(
                    record, target_date, is_user_provide_date
                ).rstrip()
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
                "topic": "quy_dinh_chung_ly_hon",
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
