"""Retriever cho chủ đề hôn nhân chấm dứt do vợ/chồng chết — Điều 65-67 Luật HNGD 2014.

Pipeline 3 bước:
    1. CLASSIFY  -> LLM chọn 1-2 template (registry topic hon_nhan_cham_dut_do_vo_chong_chet).
    2. EXTRACT   -> 1 LLM call mỗi template (params + thời điểm sự kiện).
    3. EXECUTE   -> chạy Cypher qua asyncio.to_thread → encode_context_record.

Output: dict ``{"contexts": list[str], "debug": str}``.
"""
from __future__ import annotations

import asyncio
import json
from datetime import date
from typing import Any, List, get_args, get_origin

from pydantic import BaseModel, Field

from adapter.config import driver, build_llm, RETRIEVER_LLM
from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.extract_schema import (
    build_params_with_date_schema,
    split_params_and_date,
)
from adapter.cypher_templates.hon_nhan_cham_dut_do_vo_chong_chet import (
    HON_NHAN_CHAM_DUT_DO_VO_CHONG_CHET_REGISTRY,
)
from adapter.cypher_templates.hon_nhan_cham_dut_do_vo_chong_chet.term_mapping import (
    resolve_term,
)
from adapter.graph_viz import save_lazy_viz_stub
from utils.legal_context_codec import encode_context_record


hon_nhan_cham_dut_do_vo_chong_chet_description = {
    "type": "function",
    "function": {
        "name": "hon_nhan_cham_dut_do_vo_chong_chet",
        "description": (
            "Tra cứu quy định về chấm dứt hôn nhân do vợ hoặc chồng chết thực tế "
            "hoặc bị Tòa án tuyên bố là đã chết; quản lý/chia tài sản khi một bên chết "
            "(Điều 66); khôi phục hôn nhân và giải quyết tài sản khi người bị tuyên bố "
            "đã chết trở về (Điều 67). Phạm vi Điều 65-67 Luật HNGD 2014."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Câu hỏi về chấm dứt hôn nhân do chết/tuyên bố đã chết, "
                        "tài sản khi một bên chết hoặc người bị tuyên bố đã chết trở về."
                    ),
                }
            },
            "required": ["query"],
        },
    },
}


class TemplateChoice(BaseModel):
    template_name: str = Field(
        description="Tên template — phải khớp 1 trong 4 template đã liệt kê."
    )
    reason: str = Field(description="Lý do ngắn (1 câu) chọn template này.")


class TemplateChoiceList(BaseModel):
    choices: List[TemplateChoice] = Field(
        description="Danh sách template phù hợp. Tối đa 2. Hầu hết câu chỉ cần 1."
    )


def _build_classifier_prompt() -> str:
    descriptions = HON_NHAN_CHAM_DUT_DO_VO_CHONG_CHET_REGISTRY.descriptions()
    lines = ["Các template Cypher cho chủ đề 'Hôn nhân chấm dứt do vợ/chồng chết':\n"]
    for name, desc in descriptions.items():
        lines.append(f"\n- **{name}**:\n{desc}\n")
    return (
        "Bạn là router chọn template Cypher để truy xuất ngữ cảnh pháp lý cho "
        "câu hỏi về HÔN NHÂN CHẤM DỨT DO VỢ/CHỒNG CHẾT theo Luật Hôn nhân và Gia đình 2014.\n\n"
        "QUY TẮC ƯU TIÊN (theo thứ tự):\n"
        "1. Có 'trở về/quay về/còn sống' và hỏi hôn nhân cũ có khôi phục, hôn nhân sau có "
        "hiệu lực, quyết định ly hôn còn hiệu lực "
        "→ khoi_phuc_quan_he_hon_nhan_khi_nguoi_bi_tuyen_bo_da_chet_tro_ve.\n"
        "2. Có 'trở về/quay về/còn sống' và hỏi tài sản, chia lại, tài sản chung cũ, "
        "tài sản có trong thời gian bị tuyên bố đã chết "
        "→ giai_quyet_tai_san_khi_nguoi_bi_tuyen_bo_da_chet_tro_ve.\n"
        "3. Cùng câu có cả câu hỏi khôi phục hôn nhân và tài sản → chọn HAI template "
        "Điều 67, theo thứ tự hôn nhân trước, tài sản sau.\n"
        "4. Không có 'trở về', nhưng hỏi quản lý tài sản chung, chia tài sản/di sản, "
        "hạn chế chia di sản hoặc tài sản kinh doanh khi một bên chết/tuyên bố đã chết "
        "→ giai_quyet_tai_san_khi_mot_ben_chet.\n"
        "5. Hỏi có chấm dứt không, thời điểm chấm dứt, chết, bị tuyên bố đã chết, "
        "biệt tích bao nhiêu năm để kết hôn người mới "
        "→ thoi_diem_cham_dut_hon_nhan_do_chet.\n"
        "6. Mặc định một template; tối đa hai template. KHÔNG bịa template name.\n\n"
        "RANH GIỚI:\n"
        "- 'Tòa tuyên bố mất tích' KHÔNG được normalize thành 'tuyên bố đã chết'.\n"
        "- Biệt tích không tự chấm dứt hôn nhân; Điều 65 không quy định số năm tuyên bố đã chết.\n"
        "- Hỏi thủ tục ly hôn với người mất tích (không hỏi chết/tuyên bố đã chết) → topic ly hôn.\n"
        "- Chi tiết thừa kế, phần di sản → topic thừa kế/pháp luật dân sự.\n"
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
        print(f"[Classifier-hon_nhan_cham_dut] Lỗi: {exc}. Fallback thời điểm.")
        return [
            TemplateChoice(
                template_name="thoi_diem_cham_dut_hon_nhan_do_chet",
                reason="Fallback do lỗi LLM",
            )
        ]

    valid_names = set(HON_NHAN_CHAM_DUT_DO_VO_CHONG_CHET_REGISTRY.names())
    valid = [c for c in result.choices if c.template_name in valid_names]
    if not valid and result.choices:
        bad = [c.template_name for c in result.choices]
        print(f"[Classifier-hon_nhan_cham_dut] Template không hợp lệ: {bad}. Fallback.")
        valid = [
            TemplateChoice(
                template_name="thoi_diem_cham_dut_hon_nhan_do_chet",
                reason="Fallback template không hợp lệ",
            )
        ]
    if not valid:
        valid = [
            TemplateChoice(
                template_name="thoi_diem_cham_dut_hon_nhan_do_chet",
                reason="Fallback mặc định",
            )
        ]
    print(
        f"[Classifier-hon_nhan_cham_dut] Chọn: "
        f"{[(c.template_name, c.reason) for c in valid]}"
    )
    return valid[:2]


_EXTRACT_SYS_PROMPT_BASE = (
    "Bạn là chuyên gia trích xuất tham số cho câu Cypher truy xuất luật pháp "
    "về hôn nhân chấm dứt do vợ/chồng chết. Điền chính xác các trường schema `{schema_name}`.\n\n"
    "QUY TẮC:\n"
    "1. ĐỌC description từng field — có bảng map ngữ thông tục → enum chuẩn.\n"
    "2. Không suy luận được → chọn giá trị mặc định an toàn (khong_ro, tong_quat).\n"
    "3. KHÔNG bịa enum ngoài Literal.\n"
    "4. `tuyen_bo_mat_tich` và `tuyen_bo_da_chet` là hai giá trị khác nhau — không hoán đổi.\n"
    "5. `thoi_diem_su_kien`: mốc thời gian sự kiện 'YYYY-MM-DD' hoặc null nếu "
    "câu hỏi không nêu ngày/tháng/năm cụ thể."
)

_TEMPLATE_TERM_ALIASES: dict[str, dict[str, str]] = {
    "giai_quyet_tai_san_khi_mot_ben_chet": {"khia_canh_tai_san_66": "khia_canh_tai_san"},
    "giai_quyet_tai_san_khi_nguoi_bi_tuyen_bo_da_chet_tro_ve": {
        "khia_canh_tai_san_67": "khia_canh_tai_san"
    },
}

_BROAD_DEFAULTS = frozenset({"khong_ro", "chua_ro", "tat_ca", "tong_quat", None, ""})


def _literal_values(schema: type[BaseModel], field_name: str) -> frozenset[str] | None:
    if field_name not in schema.model_fields:
        return None
    annotation = schema.model_fields[field_name].annotation
    if get_origin(annotation) is not None:
        args = get_args(annotation)
        if args:
            return frozenset(str(a) for a in args)
    return None


def _normalize_with_term_mapping(
    params: BaseModel, query: str, template: CypherTemplate
) -> BaseModel:
    data = params.model_dump()
    changed = False
    aliases = _TEMPLATE_TERM_ALIASES.get(template.name, {})

    for map_field, target_field in aliases.items():
        if target_field not in data:
            continue
        current = data.get(target_field)
        if current not in _BROAD_DEFAULTS:
            continue
        valid = _literal_values(template.params_schema, target_field)
        resolved = resolve_term(map_field, query, valid)
        if resolved and resolved != current:
            print(f"[term_mapping] {target_field}: '{current}' → '{resolved}'")
            data[target_field] = resolved
            changed = True

    for field_name, field_info in template.params_schema.model_fields.items():
        if field_name in aliases.values():
            continue
        current = data.get(field_name)
        if current not in _BROAD_DEFAULTS:
            continue
        valid = _literal_values(template.params_schema, field_name)
        resolved = resolve_term(field_name, query, valid)
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
    params = _normalize_with_term_mapping(params, query, template)
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


async def hon_nhan_cham_dut_do_vo_chong_chet(query: str) -> dict[str, Any]:
    """3 bước: classify → extract → execute → normalize."""
    print(f"[Agent hon_nhan_cham_dut_do_vo_chong_chet] Đang xử lý: '{query}'...")

    choices = await _classify_templates(query)

    templates: List[CypherTemplate] = []
    extract_tasks = []
    for choice in choices:
        template = HON_NHAN_CHAM_DUT_DO_VO_CHONG_CHET_REGISTRY.get(choice.template_name)
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
                    retriever_name="hon_nhan_cham_dut_do_vo_chong_chet",
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
                "topic": "hon_nhan_cham_dut_do_vo_chong_chet",
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
