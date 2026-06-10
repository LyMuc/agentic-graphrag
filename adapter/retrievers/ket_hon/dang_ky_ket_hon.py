"""Retriever cho chủ đề "Đăng ký kết hôn" — Đ8-9, Đ13 HNGD; Đ11,17-18,37-38 Hộ tịch.

Pipeline 3 bước:
    1. CLASSIFY  -> LLM chọn 1+ template (registry topic 'dang_ky_ket_hon').
    2. EXTRACT   -> 1 LLM call mỗi template (params + thời điểm sự kiện).
    3. EXECUTE   -> chạy Cypher qua asyncio.to_thread → chuan_hoa_Context_cho_LLM.

Output: dict ``{"contexts": list[str], "debug": str}``.
"""
from __future__ import annotations

import asyncio
import json
import re
from datetime import date
from typing import Any, List

from pydantic import BaseModel, Field

from adapter.config import driver, build_llm, RETRIEVER_LLM
from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.extract_schema import (
    build_params_with_date_schema,
    split_params_and_date,
)
from adapter.cypher_templates.dang_ky_ket_hon import DANG_KY_KET_HON_REGISTRY
from adapter.cypher_templates.dang_ky_ket_hon.term_mapping import resolve_term
from adapter.graph_viz import save_lazy_viz_stub
from utils.utils import chuan_hoa_Context_cho_LLM


dang_ky_ket_hon_description = {
    "type": "function",
    "function": {
        "name": "dang_ky_ket_hon",
        "description": (
            "Lấy thông tin quy định về đăng ký kết hôn: thẩm quyền/nơi đăng ký, điều kiện, "
            "thủ tục, thời hạn xác minh, từ chối đăng ký, nội dung/cấp Giấy chứng nhận, "
            "kết hôn lại sau ly hôn và đăng ký lại khi mất Sổ/bản chính."
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
        description="Tên template — phải khớp 1 trong 9 template đã liệt kê."
    )
    reason: str = Field(description="Lý do ngắn (1 câu) chọn template này.")


class TemplateChoiceList(BaseModel):
    choices: List[TemplateChoice] = Field(
        description="Danh sách template phù hợp. Tối đa 2. Hầu hết câu chỉ cần 1."
    )


def _build_classifier_prompt() -> str:
    descriptions = DANG_KY_KET_HON_REGISTRY.descriptions()
    lines = ["Các template Cypher cho chủ đề 'Đăng ký kết hôn':\n"]
    for name, desc in descriptions.items():
        lines.append(f"\n- **{name}**:\n{desc}\n")
    return (
        "Bạn là router chọn template Cypher để truy xuất ngữ cảnh pháp lý cho "
        "câu hỏi về ĐĂNG KÝ KẾT HÔN.\n\n"
        "QUY TẮC ƯU TIÊN (theo thứ tự):\n"
        "1. 'Ở đâu', 'nơi nào', 'cơ quan nào', 'cấp nào', 'tạm trú', 'nhà vợ/nhà chồng', "
        "'khác tỉnh', 'có được đăng ký ở...' -> noi_va_tham_quyen_dang_ky_ket_hon.\n"
        "2. 'Thủ tục/quy trình/trình tự', 'hồ sơ gì', 'cùng có mặt', 'nhờ/ủy quyền người khác' "
        "-> thu_tuc_dang_ky_ket_hon.\n"
        "3. 'Bao lâu/bao nhiêu ngày' với xác minh hoặc giải quyết hồ sơ "
        "-> thoi_han_xac_minh_dang_ky_ket_hon (không chọn thủ tục chỉ vì câu kể nộp hồ sơ).\n"
        "4. 'Điều kiện gì', 'không đăng ký có được công nhận', 'trước lễ cưới bao lâu', "
        "'sai thẩm quyền' -> dieu_kien_va_gia_tri_dang_ky_ket_hon.\n"
        "5. 'Đã ly hôn, quay lại/xác lập lại quan hệ vợ chồng' "
        "-> ket_hon_lai_sau_ly_hon (KHÔNG chọn dang_ky_lai_ket_hon).\n"
        "6. 'Bị từ chối/không được chấp nhận' -> tu_choi_dang_ky_ket_hon.\n"
        "7. 'Giấy chứng nhận gồm/nội dung/thông tin gì' -> noi_dung_giay_chung_nhan_ket_hon.\n"
        "8. 'Lễ trao/trao giấy/mấy bản chính' -> cap_va_trao_giay_chung_nhan_ket_hon.\n"
        "9. 'Đăng ký lại/cấp lại giấy' kèm mất Sổ hộ tịch hoặc bản chính "
        "-> dang_ky_lai_ket_hon.\n"
        "10. 'Nơi đăng ký kết hôn lại ở đâu' (trọng tâm địa điểm) "
        "-> noi_va_tham_quyen_dang_ky_ket_hon với tinh_huong_ket_hon=ket_hon_lai_sau_ly_hon.\n"
        "11. 'Cơ quan mới nhất năm 20XX' -> noi_va_tham_quyen; mốc năm vào thoi_diem_su_kien.\n"
        "12. Chi tiết tuổi, huyết thống, cấm kết hôn -> topic dieu_kien_ket_hon.\n"
        "13. Mặc định 1 template/câu; tối đa 2 khi có hai yêu cầu độc lập.\n"
        "14. KHÔNG chọn cả ket_hon_lai_sau_ly_hon và dang_ky_lai_ket_hon trừ khi hỏi hai nghiệp vụ khác nhau.\n"
        "15. KHÔNG bịa template name ngoài danh sách.\n"
        + "".join(lines)
    )


def _safety_net_classify(query: str, choices: List[TemplateChoice]) -> List[TemplateChoice]:
    """Phân biệt kết hôn lại sau ly hôn vs đăng ký lại giấy."""
    q = query.lower()
    has_ly_hon_lai = bool(
        re.search(
            r"ly hôn.*(quay lại|kết hôn lại|xác lập lại|tái hôn)|"
            r"(quay lại|kết hôn lại|xác lập lại).*(ly hôn|vợ chồng cũ)",
            q,
        )
    )
    has_dang_ky_lai = bool(
        re.search(
            r"(cấp lại|đăng ký lại).*(giấy|sổ)|"
            r"mất.*(sổ hộ tịch|bản chính|giấy kết hôn)",
            q,
        )
    )
    names = {c.template_name for c in choices}
    if has_ly_hon_lai and not has_dang_ky_lai and "dang_ky_lai_ket_hon" in names:
        choices = [
            c for c in choices if c.template_name != "dang_ky_lai_ket_hon"
        ] or choices
    if has_dang_ky_lai and not has_ly_hon_lai and "ket_hon_lai_sau_ly_hon" in names:
        choices = [
            c for c in choices if c.template_name != "ket_hon_lai_sau_ly_hon"
        ] or choices
    if re.search(r"bao lâu|bao nhiêu ngày|mấy ngày", q) and re.search(
        r"xác minh|giải quyết.*hồ sơ", q
    ):
        if not any(c.template_name == "thoi_han_xac_minh_dang_ky_ket_hon" for c in choices):
            choices = [
                TemplateChoice(
                    template_name="thoi_han_xac_minh_dang_ky_ket_hon",
                    reason="Safety-net: câu hỏi thời hạn xác minh/giải quyết",
                )
            ] + choices
    return choices[:2]


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
        print(f"[Classifier-dang_ky_ket_hon] Lỗi: {exc}. Fallback thẩm quyền.")
        return [
            TemplateChoice(
                template_name="noi_va_tham_quyen_dang_ky_ket_hon",
                reason="Fallback do lỗi LLM",
            )
        ]

    valid_names = set(DANG_KY_KET_HON_REGISTRY.names())
    valid = [c for c in result.choices if c.template_name in valid_names]
    if not valid and result.choices:
        bad = [c.template_name for c in result.choices]
        print(f"[Classifier-dang_ky_ket_hon] Template không hợp lệ: {bad}. Fallback.")
        valid = [
            TemplateChoice(
                template_name="noi_va_tham_quyen_dang_ky_ket_hon",
                reason="Fallback template không hợp lệ",
            )
        ]
    if not valid:
        valid = [
            TemplateChoice(
                template_name="noi_va_tham_quyen_dang_ky_ket_hon",
                reason="Fallback mặc định",
            )
        ]
    valid = _safety_net_classify(query, valid)
    print(
        f"[Classifier-dang_ky_ket_hon] Chọn: "
        f"{[(c.template_name, c.reason) for c in valid]}"
    )
    return valid[:2]


_EXTRACT_SYS_PROMPT_BASE = (
    "Bạn là chuyên gia trích xuất tham số cho câu Cypher truy xuất luật pháp "
    "về đăng ký kết hôn. Điền chính xác các trường schema `{schema_name}`.\n\n"
    "QUY TẮC:\n"
    "1. ĐỌC description từng field — có bảng map ngữ thông tục → enum chuẩn.\n"
    "2. Không suy luận được → chọn giá trị mặc định an toàn (khong_ro, tong_quat).\n"
    "3. KHÔNG bịa enum ngoài Literal.\n"
    "4. Plain 'kết hôn lại' không đủ để chọn đăng ký lại giấy; cần ngữ cảnh mất Sổ/bản chính.\n"
    "5. `thoi_diem_su_kien`: mốc thời gian sự kiện 'YYYY-MM-DD' hoặc null nếu "
    "câu hỏi không nêu ngày/tháng/năm cụ thể. Nếu chỉ nêu năm (vd 2025) → '2025-12-31'."
)

_ENUM_FIELDS = {
    "boi_canh_chu_the",
    "loai_noi_cu_tru",
    "ben_co_noi_cu_tru",
    "khia_canh_tham_quyen",
    "tinh_huong_ket_hon",
    "tinh_trang_dang_ky",
    "khia_canh_dieu_kien_gia_tri",
    "tinh_trang_truoc_do",
    "khia_canh_ket_hon_lai",
    "cap_dang_ky",
    "khia_canh_thu_tuc",
    "khia_canh_thoi_han",
    "co_can_xac_minh",
    "ly_do_tu_choi",
    "khia_canh_tu_choi",
    "khia_canh_noi_dung",
    "khia_canh_cap_trao",
    "yeu_to_nuoc_ngoai",
    "khia_canh_dang_ky_lai",
    "tinh_trang_luu_tru",
    "thoi_diem_dang_ky_truoc",
    "nguoi_yeu_cau_con_song",
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


async def dang_ky_ket_hon(query: str) -> dict[str, Any]:
    """3 bước: classify → extract → execute → normalize."""
    print(f"[Agent dang_ky_ket_hon] Đang xử lý: '{query}'...")

    choices = await _classify_templates(query)

    templates: List[CypherTemplate] = []
    extract_tasks = []
    for choice in choices:
        template = DANG_KY_KET_HON_REGISTRY.get(choice.template_name)
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
                "topic": "dang_ky_ket_hon",
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
