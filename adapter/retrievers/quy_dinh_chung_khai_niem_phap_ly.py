"""Retriever cho chủ đề quy định chung và khái niệm pháp lý — Đ1-7 Luật HNGD 2014.

Pipeline 3 bước:
    1. CLASSIFY  -> LLM chọn 1+ template (registry topic).
    2. EXTRACT   -> params + thời điểm sự kiện.
    3. EXECUTE   -> Cypher semantic seed → chuan_hoa_Context_cho_LLM.

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
from adapter.cypher_templates.quy_dinh_chung_khai_niem_phap_ly import (
    QUY_DINH_CHUNG_KHAI_NIEM_PHAP_LY_REGISTRY,
)
from adapter.cypher_templates.quy_dinh_chung_khai_niem_phap_ly.term_mapping import (
    resolve_term,
)
from adapter.graph_viz import save_lazy_viz_stub
from utils.utils import chuan_hoa_Context_cho_LLM


quy_dinh_chung_khai_niem_phap_ly_description = {
    "type": "function",
    "function": {
        "name": "quy_dinh_chung_khai_niem_phap_ly",
        "description": (
            "Tra cứu quy định chung và khái niệm pháp lý Luật Hôn nhân và Gia đình 2014 "
            "(Điều 1-7): nguyên tắc cơ bản, khái niệm, trách nhiệm Nhà nước/xã hội, "
            "hành vi bị cấm, phạm vi ba đời, áp dụng luật liên quan và tập quán."
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
        description="Tên template — phải khớp 1 trong 5 template đã liệt kê."
    )
    reason: str = Field(description="Lý do ngắn (1 câu) chọn template này.")


class TemplateChoiceList(BaseModel):
    choices: List[TemplateChoice] = Field(
        description="Danh sách template phù hợp. Tối đa 2. Hầu hết câu chỉ cần 1."
    )


def _build_classifier_prompt() -> str:
    descriptions = QUY_DINH_CHUNG_KHAI_NIEM_PHAP_LY_REGISTRY.descriptions()
    lines = [
        "Các template Cypher cho chủ đề 'Quy định chung và khái niệm pháp lý':\n"
    ]
    for name, desc in descriptions.items():
        lines.append(f"\n- **{name}**:\n{desc}\n")
    return (
        "Bạn là router chọn template Cypher để truy xuất ngữ cảnh pháp lý cho "
        "câu hỏi về QUY ĐỊNH CHUNG VÀ KHÁI NIỆM PHÁP LÝ (Điều 1-7 Luật HNGD 2014).\n\n"
        "QUY TẮC ƯU TIÊN (theo thứ tự):\n"
        "1. Có ba đời, phạm vi ba đời, trực hệ, cận huyết, con chú/bác/cô/cậu/dì "
        "hoặc hỏi gồm những ai trong họ hàng "
        "→ pham_vi_ba_doi_va_quan_he_than_thich.\n"
        "2. Có hành vi bị cấm, ngoại tình, đang có vợ/chồng, chung sống như vợ chồng, "
        "sống chung, ly thân, qua lại với người khác, bạo lực gia đình, yêu sách của cải "
        "→ bao_ve_che_do_va_hanh_vi_bi_cam.\n"
        "3. Có trách nhiệm Nhà nước/xã hội, thống nhất quản lý, Chính phủ, bộ, UBND, "
        "cơ quan tổ chức, nhà trường "
        "→ trach_nhiem_nha_nuoc_xa_hoi.\n"
        "4. Có nguyên tắc, một vợ một chồng, tự nguyện tiến bộ, vợ chồng bình đẳng "
        "mà không mô tả hành vi vi phạm "
        "→ nguyen_tac_che_do_hon_nhan_gia_dinh.\n"
        "5. Có dạng X là gì, được hiểu thế nào, bắt đầu/kết thúc khi nào, phạm vi điều chỉnh, "
        "áp dụng tập quán, áp dụng Bộ luật dân sự "
        "→ quy_dinh_chung_va_khai_niem_phap_ly.\n"
        "6. Vừa hỏi khái niệm chung sống như vợ chồng vừa đánh giá vi phạm một vợ một chồng "
        "→ ưu tiên bao_ve_che_do_va_hanh_vi_bi_cam.\n"
        "7. Mặc định 1 template/câu; tối đa 2 khi có hai yêu cầu pháp lý độc lập.\n"
        "8. Fallback → quy_dinh_chung_va_khai_niem_phap_ly.\n"
        + "".join(lines)
    )


def _safety_net_classify(query: str, choices: List[TemplateChoice]) -> List[TemplateChoice]:
    q = query.lower()
    names = {c.template_name for c in choices}
    valid_names = set(QUY_DINH_CHUNG_KHAI_NIEM_PHAP_LY_REGISTRY.names())

    if re.search(r"ba đời|trực hệ|cận huyết", q):
        if "pham_vi_ba_doi_va_quan_he_than_thich" not in names:
            choices = [
                TemplateChoice(
                    template_name="pham_vi_ba_doi_va_quan_he_than_thich",
                    reason="Safety-net: ba đời/trực hệ",
                )
            ] + choices

    if re.search(
        r"ngoại tình|chung sống như vợ chồng|sống chung|ly thân|qua lại.*người khác|"
        r"hành vi bị cấm",
        q,
    ):
        if "bao_ve_che_do_va_hanh_vi_bi_cam" not in names:
            choices = [
                TemplateChoice(
                    template_name="bao_ve_che_do_va_hanh_vi_bi_cam",
                    reason="Safety-net: hành vi bị cấm/ngoại tình",
                )
            ] + choices

    if re.search(
        r"thống nhất quản lý|chính phủ|ủy ban nhân dân|\bubnd\b|trách nhiệm.*nhà nước",
        q,
    ):
        if "trach_nhiem_nha_nuoc_xa_hoi" not in names:
            choices = [
                TemplateChoice(
                    template_name="trach_nhiem_nha_nuoc_xa_hoi",
                    reason="Safety-net: trách nhiệm Nhà nước",
                )
            ] + choices

    if re.search(r"một vợ một chồng|nguyên tắc cơ bản", q):
        if not any(
            c.template_name == "bao_ve_che_do_va_hanh_vi_bi_cam"
            for c in choices
        ) and "nguyen_tac_che_do_hon_nhan_gia_dinh" not in names:
            choices = [
                TemplateChoice(
                    template_name="nguyen_tac_che_do_hon_nhan_gia_dinh",
                    reason="Safety-net: nguyên tắc",
                )
            ] + choices

    choices = [c for c in choices if c.template_name in valid_names]
    if not choices:
        choices = [
            TemplateChoice(
                template_name="quy_dinh_chung_va_khai_niem_phap_ly",
                reason="Safety-net fallback",
            )
        ]
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
        print(f"[Classifier-quy_dinh_chung] Lỗi: {exc}. Fallback.")
        return [
            TemplateChoice(
                template_name="quy_dinh_chung_va_khai_niem_phap_ly",
                reason="Fallback do lỗi LLM",
            )
        ]

    valid_names = set(QUY_DINH_CHUNG_KHAI_NIEM_PHAP_LY_REGISTRY.names())
    valid = [c for c in result.choices if c.template_name in valid_names]
    if not valid and result.choices:
        bad = [c.template_name for c in result.choices]
        print(f"[Classifier-quy_dinh_chung] Template không hợp lệ: {bad}. Fallback.")
        valid = [
            TemplateChoice(
                template_name="quy_dinh_chung_va_khai_niem_phap_ly",
                reason="Fallback template không hợp lệ",
            )
        ]
    if not valid:
        valid = [
            TemplateChoice(
                template_name="quy_dinh_chung_va_khai_niem_phap_ly",
                reason="Fallback mặc định",
            )
        ]
    valid = _safety_net_classify(query, valid)
    print(
        f"[Classifier-quy_dinh_chung] Chọn: "
        f"{[(c.template_name, c.reason) for c in valid]}"
    )
    return valid[:2]


_EXTRACT_SYS_PROMPT_BASE = (
    "Bạn là chuyên gia trích xuất tham số cho câu Cypher truy xuất luật pháp "
    "về quy định chung và khái niệm pháp lý (Điều 1-7 Luật HNGD 2014). "
    "Điền chính xác các trường schema `{schema_name}`.\n\n"
    "QUY TẮC:\n"
    "1. ĐỌC description từng field — có bảng map ngữ thông tục → enum chuẩn.\n"
    "2. Không suy luận được → chọn giá trị mặc định an toàn (khong_ro, tong_quat).\n"
    "3. KHÔNG bịa enum ngoài Literal.\n"
    "4. Ly thân không map thành da_ly_hon.\n"
    "5. Ngoại tình một mình không map chung_song_nhu_vo_chong nếu câu không mô tả "
    "sống chung/ăn ở như vợ chồng.\n"
    "6. `thoi_diem_su_kien`: mốc thời gian 'YYYY-MM-DD' hoặc null nếu không nêu ngày cụ thể."
)

_ENUM_FIELDS = {
    "khia_canh_nguyen_tac",
    "chu_the_trach_nhiem",
    "khia_canh_trach_nhiem",
    "nhom_hanh_vi",
    "dang_quan_he_thuc_te",
    "tinh_trang_hon_nhan",
    "khia_canh_bao_ve_cam",
    "loai_quan_he",
    "khia_canh_ba_doi",
    "noi_dung_phap_ly",
    "khia_canh_khai_niem",
    "muc_do_chi_tiet",
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


async def quy_dinh_chung_khai_niem_phap_ly(query: str) -> dict[str, Any]:
    """3 bước: classify → extract → execute → normalize."""
    print(f"[Agent quy_dinh_chung_khai_niem_phap_ly] Đang xử lý: '{query}'...")

    choices = await _classify_templates(query)

    templates: List[CypherTemplate] = []
    extract_tasks = []
    for choice in choices:
        template = QUY_DINH_CHUNG_KHAI_NIEM_PHAP_LY_REGISTRY.get(choice.template_name)
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
                "topic": "quy_dinh_chung_khai_niem_phap_ly",
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
