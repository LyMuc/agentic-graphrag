"""Retriever cho chủ đề "Kết hôn trái pháp luật" — Đ3 K6, Đ10-12 + TTLT 01/2016 Đ2-4.

Pipeline 3 bước:
    1. CLASSIFY  -> LLM chọn 1+ template (registry topic 'ket_hon_trai_phap_luat').
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
from adapter.cypher_templates.ket_hon_trai_phap_luat import KET_HON_TRAI_PHAP_LUAT_REGISTRY
from adapter.cypher_templates.ket_hon_trai_phap_luat.term_mapping import resolve_term
from adapter.graph_viz import save_lazy_viz_stub
from utils.utils import chuan_hoa_Context_cho_LLM


ket_hon_trai_phap_luat_description = {
    "type": "function",
    "function": {
        "name": "ket_hon_trai_phap_luat",
        "description": (
            "Tra cứu kết hôn trái pháp luật: định nghĩa, căn cứ hủy, ai có quyền yêu cầu "
            "Tòa án hủy, thẩm quyền/hồ sơ, xử lý công nhận-hủy-ly hôn khi điều kiện thay đổi, "
            "hậu quả sau hủy (Đ3 K6, Đ10-12, TTLT 01/2016 Đ2-4). "
            "BẮT BUỘC khi hỏi hủy kết hôn trái pháp luật, quyền yêu cầu hủy, căn cứ hủy. "
            "KHÔNG dùng cho: điều kiện kết hôn trước đăng ký (dieu_kien_ket_hon); "
            "thủ tục đăng ký kết hôn (dang_ky_ket_hon); chung sống không đăng ký sâu "
            "(chung_song_nhu_vo_chong); tố tụng chi tiết/án phí (to_tung_hon_nhan); "
            "xử phạt hành chính/hình sự (xu_phat_vi_pham); thừa kế/di sản."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Câu hỏi về kết hôn trái pháp luật, quyền yêu cầu hủy, "
                        "thủ tục/hồ sơ hủy, công nhận-hủy-ly hôn hoặc hậu quả sau hủy."
                    ),
                }
            },
            "required": ["query"],
        },
    },
}


class TemplateChoice(BaseModel):
    template_name: str = Field(
        description="Tên template — phải khớp 1 trong 5 template đã liệt kê."
    )
    reason: str = Field(description="Lý do ngắn (1 câu) chọn template này.")


class TemplateChoiceList(BaseModel):
    choices: List[TemplateChoice] = Field(
        description="Danh sách template phù hợp. Tối đa 3. Hầu hết câu chỉ cần 1."
    )


def _build_classifier_prompt() -> str:
    descriptions = KET_HON_TRAI_PHAP_LUAT_REGISTRY.descriptions()
    lines = ["Các template Cypher cho chủ đề 'Kết hôn trái pháp luật':\n"]
    for name, desc in descriptions.items():
        lines.append(f"\n- **{name}**:\n{desc}\n")
    return (
        "Bạn là router chọn template Cypher để truy xuất ngữ cảnh pháp lý cho "
        "câu hỏi về KẾT HÔN TRÁI PHÁP LUẬT (Đ3 K6, Đ10-12, TTLT 01/2016 Đ2-4).\n\n"
        "QUY TẮC ƯU TIÊN (theo thứ tự):\n"
        "1. 'Ai có quyền yêu cầu', cha/mẹ/dì/chị/hàng xóm/Hội phụ nữ, 'tự mình yêu cầu' "
        "→ quyen_yeu_cau_huy_ket_hon_trai_phap_luat.\n"
        "2. 'Hồ sơ/giấy tờ/chứng cứ', 'cơ quan nào/thẩm quyền', 'mất giấy kết hôn', "
        "'không đăng ký', 'sai thẩm quyền' "
        "→ thu_ly_tham_quyen_va_ho_so_huy_ket_hon.\n"
        "3. 'Nay đã đủ tuổi/đủ điều kiện', 'cùng đồng ý tiếp tục', 'được công nhận không', "
        "cấu hình công nhận-hủy-ly hôn khi Tòa giải quyết "
        "→ xu_ly_yeu_cau_huy_va_cong_nhan_hon_nhan.\n"
        "4. 'Hậu quả pháp lý', 'tài sản/con chung/nghĩa vụ/hợp đồng sau khi hủy' "
        "→ hau_qua_phap_ly_huy_ket_hon_trai_phap_luat.\n"
        "5. 'Là gì', 'trường hợp nào', 'căn cứ hủy' "
        "→ khai_niem_va_can_cu_ket_hon_trai_phap_luat.\n"
        "6. Câu 10 và 25 (quyền + tài sản/thừa kế): chọn quyen_yeu_cau_huy... "
        "VÀ hau_qua_phap_ly_huy_ket_hon_trai_phap_luat.\n"
        "7. Dì, chị, hàng xóm KHÔNG có quyền yêu cầu trực tiếp — chỉ đề nghị theo Đ10 K3.\n"
        "8. Câu hỏi thuần điều kiện kết hôn/xử phạt Điều 5 → KHÔNG chọn template này.\n"
        "9. Mặc định 1 template/câu; tối đa 3 khi có nhiều yêu cầu độc lập.\n"
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
    fallback = "khai_niem_va_can_cu_ket_hon_trai_phap_luat"
    try:
        result: TemplateChoiceList = await structured_llm.ainvoke(messages)
    except Exception as exc:
        print(f"[Classifier-ket_hon_trai_phap_luat] Lỗi: {exc}. Fallback {fallback}.")
        return [
            TemplateChoice(template_name=fallback, reason="Fallback do lỗi LLM")
        ]

    valid_names = set(KET_HON_TRAI_PHAP_LUAT_REGISTRY.names())
    valid = [c for c in result.choices if c.template_name in valid_names]
    if not valid and result.choices:
        bad = [c.template_name for c in result.choices]
        print(f"[Classifier-ket_hon_trai_phap_luat] Template không hợp lệ: {bad}. Fallback.")
        valid = [
            TemplateChoice(
                template_name=fallback,
                reason="Fallback template không hợp lệ",
            )
        ]
    if not valid:
        valid = [
            TemplateChoice(template_name=fallback, reason="Fallback mặc định")
        ]
    print(
        f"[Classifier-ket_hon_trai_phap_luat] Chọn: "
        f"{[(c.template_name, c.reason) for c in valid]}"
    )
    return valid[:3]


_EXTRACT_SYS_PROMPT_BASE = (
    "Bạn là chuyên gia trích xuất tham số cho câu Cypher truy xuất luật pháp "
    "về kết hôn trái pháp luật. Điền chính xác các trường schema `{schema_name}`.\n\n"
    "QUY TẮC:\n"
    "1. ĐỌC description từng field — có bảng map ngữ thông tục → enum chuẩn.\n"
    "2. Không suy luận được → chọn giá trị mặc định an toàn (khong_ro, tong_quat).\n"
    "3. KHÔNG bịa enum ngoài Literal.\n"
    "4. `thoi_diem_su_kien`: mốc thời gian sự kiện 'YYYY-MM-DD' hoặc null nếu "
    "câu hỏi không nêu ngày/tháng/năm cụ thể."
)

_ENUM_FIELDS = {
    "khia_canh",
    "dang_vi_pham",
    "tinh_trang_dang_ky",
    "nhom_vi_pham",
    "chu_the_hoi_quyen",
    "vai_tro_tham_gia",
    "khia_canh_thu_tuc",
    "tinh_trang_giay_chung_nhan",
    "co_chung_cu_vi_pham",
    "co_yeu_cau_giai_quyet_con_tai_san",
    "trang_thai_dieu_kien_hien_tai",
    "yeu_cau_cua_hai_ben",
    "vi_pham_ban_dau",
    "co_tai_lieu_xac_dinh_thoi_diem_du_dieu_kien",
    "ket_qua_nguoi_dung_hoi",
    "khia_canh_hau_qua",
    "tinh_huong_quan_he",
    "co_con_chung",
    "co_tranh_chap_tai_san",
    "co_yeu_cau_thua_ke",
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


async def ket_hon_trai_phap_luat(query: str) -> dict[str, Any]:
    """3 bước: classify → extract → execute → normalize."""
    print(f"[Agent ket_hon_trai_phap_luat] Đang xử lý: '{query}'...")

    choices = await _classify_templates(query)

    templates: List[CypherTemplate] = []
    extract_tasks = []
    for choice in choices:
        template = KET_HON_TRAI_PHAP_LUAT_REGISTRY.get(choice.template_name)
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
                "topic": "ket_hon_trai_phap_luat",
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
