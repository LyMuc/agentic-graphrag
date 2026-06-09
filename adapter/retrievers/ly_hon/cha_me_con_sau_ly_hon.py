"""Retriever cho chủ đề "Cha mẹ, con sau ly hôn" — Điều 81-84 Luật HNGD 2014.

Pipeline 3 bước:
    1. CLASSIFY  -> LLM chọn 1+ template (registry topic 'cha_me_con_sau_ly_hon').
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
from adapter.cypher_templates.cha_me_con_sau_ly_hon import CHA_ME_CON_SAU_LY_HON_REGISTRY
from adapter.cypher_templates.cha_me_con_sau_ly_hon.term_mapping import resolve_term
from adapter.graph_viz import save_lazy_viz_stub
from utils.utils import chuan_hoa_Context_cho_LLM


cha_me_con_sau_ly_hon_description = {
    "type": "function",
    "function": {
        "name": "cha_me_con_sau_ly_hon",
        "description": (
            "Tra cứu quy định về trông nom, chăm sóc, nuôi dưỡng, giáo dục con sau ly hôn; "
            "quyền thăm nom, cấm/cản trở cha mẹ gặp con; xác định và thay đổi người trực tiếp "
            "nuôi con (Điều 81–84). BẮT BUỘC khi hỏi không cho gặp con, quyền nuôi, thăm nom "
            "sau ly hôn. KHÔNG dùng cho câu thuần cấp dưỡng (mức, phương thức, chấm dứt, "
            "cưỡng chế Đ107–120) → dùng cap_duong. Câu kết hợp nuôi con + thăm nom + cấp "
            "dưỡng nguyên tắc vẫn thuộc topic này."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Câu hỏi về quyền nuôi con, thăm nom, không cho/cấm cha mẹ gặp con "
                        "sau khi ly hôn."
                    ),
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
    descriptions = CHA_ME_CON_SAU_LY_HON_REGISTRY.descriptions()
    lines = ["Các template Cypher cho chủ đề 'Cha mẹ, con sau ly hôn':\n"]
    for name, desc in descriptions.items():
        lines.append(f"\n- **{name}**:\n{desc}\n")
    return (
        "Bạn là router chọn template Cypher để truy xuất ngữ cảnh pháp lý cho "
        "câu hỏi về CHA MẸ, CON SAU LY HÔN theo Luật Hôn nhân và Gia đình 2014 (Đ81-84).\n\n"
        "QUY TẮC ƯU TIÊN (theo thứ tự):\n"
        "1. 'Thay đổi người trực tiếp nuôi', 'giành lại quyền nuôi', 'Tòa đã giao con', "
        "người đang nuôi chết/đi tù/đi xa/không chăm sóc tốt "
        "→ thay_doi_nguoi_truc_tiep_nuoi_con.\n"
        "2. Tuổi dưới 36 tháng/dưới 3 tuổi hoặc 9/18/24 tháng và hỏi ai được nuôi "
        "→ nuoi_con_duoi_36_thang.\n"
        "3. 'Thăm nom/gặp con', 'ngăn/cấm/cản trở', 'lạm dụng thăm nom', "
        "'hạn chế quyền thăm', 'bị phạt vì cản thăm' "
        "→ tham_nom_va_can_tro_tham_nom.\n"
        "4. 'Người không trực tiếp nuôi' + toàn bộ quyền/nghĩa vụ, tôn trọng quyền "
        "sống chung, hoặc cấp dưỡng ở mức nguyên tắc (không hỏi mức/phương thức) "
        "→ quyen_nghia_vu_nguoi_khong_truc_tiep_nuoi.\n"
        "5. 'Ai được nuôi', 'giành quyền nuôi khi ly hôn', so sánh điều kiện cha/mẹ, "
        "lợi ích con, nguyện vọng con từ 07 tuổi "
        "→ xac_dinh_nguoi_truc_tiep_nuoi_con.\n"
        "6. Hỏi chung trông nom/chăm sóc/nuôi dưỡng/giáo dục hoặc ly hôn có làm mất "
        "quyền làm cha/mẹ → quyen_nghia_vu_chung_sau_ly_hon.\n"
        "7. 'Không cấp dưỡng có được thăm con không' → tham_nom_va_can_tro_tham_nom; "
        "tinh_trang_cap_duong chỉ là fact phụ.\n"
        "8. Câu vừa hỏi quyền/nghĩa vụ người không trực tiếp nuôi vừa cản thăm nom "
        "có thể chọn quyen_nghia_vu_nguoi_khong_truc_tiep_nuoi VÀ tham_nom_va_can_tro_tham_nom.\n"
        "9. Câu vừa tranh chấp người nuôi vừa hỏi cấp dưỡng nguyên tắc: chọn template "
        "nuôi con phù hợp + quyen_nghia_vu_nguoi_khong_truc_tiep_nuoi nếu cần Đ82 K2.\n"
        "10. Câu THUẦN cấp dưỡng (mức bao nhiêu, tối thiểu, phương thức, tạm ngừng, "
        "chấm dứt, cưỡng chế) → KHÔNG chọn template này; router gọi cap_duong.\n"
        "11. 'Ông bà/người thân muốn nuôi cháu' sau khi đã có người nuôi "
        "→ thay_doi_nguoi_truc_tiep_nuoi_con.\n"
        "12. Mặc định 1 template/câu; tối đa 3 khi có nhiều yêu cầu độc lập.\n"
        "13. KHÔNG bịa template name ngoài danh sách.\n"
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
        print(f"[Classifier-cha_me_con_sau_ly_hon] Lỗi: {exc}. Fallback xac_dinh.")
        return [
            TemplateChoice(
                template_name="xac_dinh_nguoi_truc_tiep_nuoi_con",
                reason="Fallback do lỗi LLM",
            )
        ]

    valid_names = set(CHA_ME_CON_SAU_LY_HON_REGISTRY.names())
    valid = [c for c in result.choices if c.template_name in valid_names]
    if not valid and result.choices:
        bad = [c.template_name for c in result.choices]
        print(f"[Classifier-cha_me_con_sau_ly_hon] Template không hợp lệ: {bad}. Fallback.")
        valid = [
            TemplateChoice(
                template_name="xac_dinh_nguoi_truc_tiep_nuoi_con",
                reason="Fallback template không hợp lệ",
            )
        ]
    if not valid:
        valid = [
            TemplateChoice(
                template_name="xac_dinh_nguoi_truc_tiep_nuoi_con",
                reason="Fallback mặc định",
            )
        ]
    print(
        f"[Classifier-cha_me_con_sau_ly_hon] Chọn: "
        f"{[(c.template_name, c.reason) for c in valid]}"
    )
    return valid[:3]


_EXTRACT_SYS_PROMPT_BASE = (
    "Bạn là chuyên gia trích xuất tham số cho câu Cypher truy xuất luật pháp "
    "về cha mẹ, con sau ly hôn. Điền chính xác các trường schema `{schema_name}`.\n\n"
    "QUY TẮC:\n"
    "1. ĐỌC description từng field — có bảng map ngữ thông tục → enum chuẩn.\n"
    "2. Không suy luận được → chọn giá trị mặc định an toàn (khong_ro, tong_quat).\n"
    "3. KHÔNG bịa enum ngoài Literal.\n"
    "4. `thoi_diem_su_kien`: mốc thời gian sự kiện 'YYYY-MM-DD' hoặc null nếu "
    "câu hỏi không nêu ngày/tháng/năm cụ thể."
)

_ENUM_FIELDS = {
    "pham_vi",
    "tinh_trang_con",
    "tinh_huong",
    "do_tuoi_con",
    "yeu_to_trong_tam",
    "ben_de_nghi_nuoi",
    "tinh_trang_nguoi_me",
    "thoa_thuan_khac",
    "co_yeu_cau_cap_duong",
    "khia_canh_nguoi_khong_truc_tiep",
    "nguoi_khong_truc_tiep_nuoi",
    "tinh_trang_cap_duong",
    "co_can_tro_tham_nom",
    "khia_canh_tham_nom",
    "chu_the_co_hanh_vi",
    "anh_huong_xau_den_con",
    "can_cu_thay_doi",
    "nguoi_yeu_cau",
    "tinh_trang_nguoi_dang_nuoi",
    "ket_qua_de_nghi",
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


async def cha_me_con_sau_ly_hon(query: str) -> dict[str, Any]:
    """3 bước: classify → extract → execute → normalize."""
    print(f"[Agent cha_me_con_sau_ly_hon] Đang xử lý: '{query}'...")

    choices = await _classify_templates(query)

    templates: List[CypherTemplate] = []
    extract_tasks = []
    for choice in choices:
        template = CHA_ME_CON_SAU_LY_HON_REGISTRY.get(choice.template_name)
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
        lazy_sources.append(
            {
                "topic": "cha_me_con_sau_ly_hon",
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
