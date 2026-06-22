"""Retriever cho chủ đề quan hệ giữa các thành viên khác trong gia đình — Đ103-106.

Pipeline 3 bước:
    1. CLASSIFY  -> LLM chọn 1+ template (registry topic).
    2. EXTRACT   -> params + thời điểm sự kiện.
    3. EXECUTE   -> Cypher semantic seed → encode_context_record.

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
from adapter.cypher_templates.quan_he_giua_cac_thanh_vien_khac_trong_gia_dinh import (
    QUAN_HE_GIUA_CAC_THANH_VIEN_KHAC_TRONG_GIA_DINH_REGISTRY,
)
from adapter.cypher_templates.quan_he_giua_cac_thanh_vien_khac_trong_gia_dinh.term_mapping import (
    resolve_term,
)
from adapter.graph_viz import save_lazy_viz_stub
from application.legal_context import encode_context_record


quan_he_giua_cac_thanh_vien_khac_trong_gia_dinh_description = {
    "type": "function",
    "function": {
        "name": "quan_he_giua_cac_thanh_vien_khac_trong_gia_dinh",
        "description": (
            "Tra cứu quyền, nghĩa vụ giữa các thành viên khác trong gia đình (Đ103-106): "
            "thành viên chung, sống chung, ông bà-cháu, anh chị em, cô dì chú cậu bác-cháu ruột; "
            "nghĩa vụ chăm sóc thường xuyên và nuôi dưỡng có điều kiện."
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
        description="Tên template — phải khớp 1 trong 8 template đã liệt kê."
    )
    reason: str = Field(description="Lý do ngắn (1 câu) chọn template này.")


class TemplateChoiceList(BaseModel):
    choices: List[TemplateChoice] = Field(
        description="Danh sách template phù hợp. Tối đa 2. Hầu hết câu chỉ cần 1."
    )


def _build_classifier_prompt() -> str:
    descriptions = QUAN_HE_GIUA_CAC_THANH_VIEN_KHAC_TRONG_GIA_DINH_REGISTRY.descriptions()
    lines = [
        "Các template Cypher cho chủ đề 'Quan hệ giữa các thành viên khác trong gia đình':\n"
    ]
    for name, desc in descriptions.items():
        lines.append(f"\n- **{name}**:\n{desc}\n")
    return (
        "Bạn là router chọn template Cypher để truy xuất ngữ cảnh pháp lý cho "
        "câu hỏi về QUYỀN, NGHĨA VỤ GIỮA CÁC THÀNH VIÊN KHÁC TRONG GIA ĐÌNH (Đ103-106).\n\n"
        "QUY TẮC ƯU TIÊN (theo thứ tự):\n"
        "1. Có 'khác gì', 'so với', đồng thời nhắc cô/dì/chú/cậu/bác và ông bà-cháu "
        "→ nuoi_duong_giua_co_di_chu_cau_bac_ruot_va_chau_ruot.\n"
        "2. Có 'sống chung', 'tiền ăn ở', 'đóng góp', 'công việc gia đình', 'lao động tạo thu nhập' "
        "→ nghia_vu_thanh_vien_song_chung.\n"
        "3. Có cô/dì/chú/cậu/bác ruột hoặc cháu ruột:\n"
        "   - Có 'nuôi dưỡng', 'không còn cha mẹ con', 'Điều 104/105' "
        "→ nuoi_duong_giua_co_di_chu_cau_bac_ruot_va_chau_ruot.\n"
        "   - Chỉ hỏi thương yêu/chăm sóc/giúp đỡ/quyền nghĩa vụ "
        "→ quyen_nghia_vu_co_di_chu_cau_bac_ruot_va_chau_ruot.\n"
        "4. Có anh/chị/em:\n"
        "   - Có 'nuôi dưỡng', 'không còn cha mẹ', 'cha mẹ không có điều kiện/bị tù/già yếu' "
        "→ nuoi_duong_giua_anh_chi_em.\n"
        "   - Chỉ hỏi quyền nghĩa vụ thương yêu/chăm sóc/giúp đỡ "
        "→ quyen_nghia_vu_anh_chi_em.\n"
        "5. Có ông bà và cháu:\n"
        "   - Có 'nuôi dưỡng', 'không có người Điều 105', 'ông bà không có con', 'cháu đã thành niên' "
        "→ nuoi_duong_giua_ong_ba_va_chau.\n"
        "   - Chỉ hỏi trông nom/chăm sóc/giáo dục/nêu gương/kính trọng/phụng dưỡng "
        "→ quyen_nghia_vu_ong_ba_va_chau.\n"
        "6. Có 'Nhà nước', 'pháp luật bảo vệ', 'nhân thân', 'tài sản' hoặc câu chung Đ103 "
        "→ quyen_nghia_vu_chung_thanh_vien_gia_dinh.\n"
        "7. Fallback → quyen_nghia_vu_chung_thanh_vien_gia_dinh.\n"
        "8. Mặc định 1 template/câu; tối đa 2 khi có hai yêu cầu độc lập.\n"
        "9. KHÔNG suy diễn 'không còn vợ/chồng' thành điều kiện Đ106.\n"
        + "".join(lines)
    )


def _safety_net_classify(query: str, choices: List[TemplateChoice]) -> List[TemplateChoice]:
    q = query.lower()
    names = {c.template_name for c in choices}

    if re.search(r"khác gì|so với", q) and re.search(
        r"ông bà|cô|dì|chú|cậu|bác", q
    ):
        if "nuoi_duong_giua_co_di_chu_cau_bac_ruot_va_chau_ruot" not in names:
            choices = [
                TemplateChoice(
                    template_name="nuoi_duong_giua_co_di_chu_cau_bac_ruot_va_chau_ruot",
                    reason="Safety-net: so sánh nuôi dưỡng",
                )
            ] + choices

    if re.search(
        r"sống chung|tiền ăn ở|đóng góp (công sức|tiền|tài sản)|công việc gia đình|lao động tạo thu nhập",
        q,
    ):
        if "nghia_vu_thanh_vien_song_chung" not in names:
            choices = [
                TemplateChoice(
                    template_name="nghia_vu_thanh_vien_song_chung",
                    reason="Safety-net: sống chung",
                )
            ] + choices

    if re.search(r"cô ruột|dì ruột|chú ruột|cậu ruột|bác ruột|cháu ruột", q):
        if re.search(r"nuôi dưỡng|không còn cha.*mẹ.*con|điều 104|điều 105", q):
            tpl = "nuoi_duong_giua_co_di_chu_cau_bac_ruot_va_chau_ruot"
        else:
            tpl = "quyen_nghia_vu_co_di_chu_cau_bac_ruot_va_chau_ruot"
        if tpl not in names:
            choices = [
                TemplateChoice(template_name=tpl, reason="Safety-net: họ hàng mở rộng")
            ] + choices

    if re.search(r"anh|chị|em", q):
        if re.search(
            r"nuôi dưỡng|không còn cha mẹ|cha mẹ .* không có điều kiện|bị tù|già yếu",
            q,
        ):
            tpl = "nuoi_duong_giua_anh_chi_em"
        else:
            tpl = "quyen_nghia_vu_anh_chi_em"
        if tpl not in names:
            choices = [
                TemplateChoice(template_name=tpl, reason="Safety-net: anh chị em")
            ] + choices

    if re.search(r"ông bà", q) and re.search(r"cháu", q):
        if re.search(
            r"nuôi dưỡng|điều 105|ông bà .* không có con|cháu .* thành niên",
            q,
        ):
            tpl = "nuoi_duong_giua_ong_ba_va_chau"
        else:
            tpl = "quyen_nghia_vu_ong_ba_va_chau"
        if tpl not in names:
            choices = [
                TemplateChoice(template_name=tpl, reason="Safety-net: ông bà-cháu")
            ] + choices

    valid_names = set(QUAN_HE_GIUA_CAC_THANH_VIEN_KHAC_TRONG_GIA_DINH_REGISTRY.names())
    choices = [c for c in choices if c.template_name in valid_names]
    if not choices:
        choices = [
            TemplateChoice(
                template_name="quyen_nghia_vu_chung_thanh_vien_gia_dinh",
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
    fallback = TemplateChoice(
        template_name="quyen_nghia_vu_chung_thanh_vien_gia_dinh",
        reason="Fallback mặc định",
    )
    try:
        result: TemplateChoiceList = await structured_llm.ainvoke(messages)
    except Exception as exc:
        print(f"[Classifier-quan_he_giua_cac_thanh_vien] Lỗi: {exc}. Fallback.")
        return [fallback]

    valid_names = set(QUAN_HE_GIUA_CAC_THANH_VIEN_KHAC_TRONG_GIA_DINH_REGISTRY.names())
    valid = [c for c in result.choices if c.template_name in valid_names]
    if not valid and result.choices:
        bad = [c.template_name for c in result.choices]
        print(f"[Classifier-quan_he_giua_cac_thanh_vien] Template không hợp lệ: {bad}.")
        valid = [fallback]
    if not valid:
        valid = [fallback]
    valid = _safety_net_classify(query, valid)
    print(
        f"[Classifier-quan_he_giua_cac_thanh_vien] Chọn: "
        f"{[(c.template_name, c.reason) for c in valid]}"
    )
    return valid[:2]


_EXTRACT_SYS_PROMPT_BASE = (
    "Bạn là chuyên gia trích xuất tham số cho câu Cypher truy xuất luật pháp "
    "về quyền, nghĩa vụ giữa các thành viên khác trong gia đình (Đ103-106). "
    "Điền chính xác các trường schema `{schema_name}`.\n\n"
    "QUY TẮC:\n"
    "1. ĐỌC description từng field — có bảng map ngữ thông tục → enum chuẩn.\n"
    "2. Không suy luận được → chọn giá trị mặc định an toàn (khong_ro, tong_quat).\n"
    "3. KHÔNG bịa enum ngoài Literal.\n"
    "4. KHÔNG suy diễn 'mất khả năng tài chính' thành 'không còn cha, mẹ, con'.\n"
    "5. KHÔNG suy diễn 'không còn vợ/chồng' thành điều kiện Đ106.\n"
    "6. 'Bị tù', 'già yếu' chỉ map cha_me_khong_co_dieu_kien khi câu nói rõ không thể trông nom.\n"
    "7. `thoi_diem_su_kien`: mốc thời gian 'YYYY-MM-DD' hoặc null nếu không nêu ngày."
)

_ENUM_FIELDS = {
    "khia_canh_chung",
    "nhom_noi_dung",
    "loai_nghia_vu_song_chung",
    "quan_he_tinh_huong",
    "khia_canh_danh_gia",
    "chieu_ong_ba_chau",
    "noi_dung_ong_ba_chau",
    "khia_canh_ong_ba_chau",
    "chieu_nuoi_duong_ong_ba_chau",
    "tinh_trang_chau",
    "nguoi_nuoi_duong_theo_dieu_105",
    "tinh_trang_con_cua_ong_ba",
    "chau_da_thanh_nien",
    "khia_canh_nuoi_duong_ong_ba_chau",
    "chieu_anh_chi_em",
    "noi_dung_anh_chi_em",
    "cung_song",
    "khia_canh_anh_chi_em",
    "tinh_trang_cha_me",
    "nguoi_duoc_nuoi_duong",
    "nguoi_thuc_hien_da_thanh_nien",
    "khia_canh_nuoi_duong_anh_chi_em",
    "doi_tuong_ho_hang",
    "chieu_ho_hang_chau",
    "noi_dung_ho_hang_chau",
    "con_cha_me_cua_chau",
    "khia_canh_ho_hang",
    "chieu_nuoi_duong_ho_hang",
    "con_cha_me_cua_nguoi_can_nuoi_duong",
    "con_con_cua_nguoi_can_nuoi_duong",
    "tinh_trang_nguoi_thuoc_dieu_104_105",
    "khia_canh_nuoi_duong_ho_hang",
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


async def quan_he_giua_cac_thanh_vien_khac_trong_gia_dinh(query: str) -> dict[str, Any]:
    """3 bước: classify → extract → execute → normalize."""
    print(f"[Agent quan_he_giua_cac_thanh_vien] Đang xử lý: '{query}'...")

    choices = await _classify_templates(query)

    templates: List[CypherTemplate] = []
    extract_tasks = []
    for choice in choices:
        template = QUAN_HE_GIUA_CAC_THANH_VIEN_KHAC_TRONG_GIA_DINH_REGISTRY.get(
            choice.template_name
        )
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
                    retriever_name="quan_he_giua_cac_thanh_vien_khac_trong_gia_dinh",
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
                "topic": "quan_he_giua_cac_thanh_vien_khac_trong_gia_dinh",
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
