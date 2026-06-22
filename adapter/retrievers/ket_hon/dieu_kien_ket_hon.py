"""Retriever cho chủ đề "Điều kiện kết hôn" — Đ3, Đ5, Đ8 Luật HNGD 2014.

Pipeline 3 bước:
    1. CLASSIFY  -> LLM chọn 1+ template (registry topic 'dieu_kien_ket_hon').
    2. EXTRACT   -> 1 LLM call mỗi template (params + thời điểm sự kiện).
    3. EXECUTE   -> chạy Cypher qua asyncio.to_thread → encode_context_record.

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
from adapter.cypher_templates.dieu_kien_ket_hon import DIEU_KIEN_KET_HON_REGISTRY
from adapter.cypher_templates.dieu_kien_ket_hon.term_mapping import resolve_term
from adapter.graph_viz import save_lazy_viz_stub
from application.legal_context import encode_context_record


dieu_kien_ket_hon_description = {
    "type": "function",
    "function": {
        "name": "dieu_kien_ket_hon",
        "description": (
            "Lấy thông tin quy định về điều kiện kết hôn: tuổi, tự nguyện, năng lực hành vi, "
            "trường hợp cấm, quan hệ huyết thống/ba đời, hôn nhân cùng giới, xác lập vợ chồng "
            "hợp pháp và các yếu tố không phải trở ngại (án treo, tín ngưỡng, hộ khẩu...)."
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
        description="Tên template — phải khớp 1 trong 10 template đã liệt kê."
    )
    reason: str = Field(description="Lý do ngắn (1 câu) chọn template này.")


class TemplateChoiceList(BaseModel):
    choices: List[TemplateChoice] = Field(
        description="Danh sách template phù hợp. Tối đa 2. Hầu hết câu chỉ cần 1."
    )


def _build_classifier_prompt() -> str:
    descriptions = DIEU_KIEN_KET_HON_REGISTRY.descriptions()
    lines = ["Các template Cypher cho chủ đề 'Điều kiện kết hôn':\n"]
    for name, desc in descriptions.items():
        lines.append(f"\n- **{name}**:\n{desc}\n")
    return (
        "Bạn là router chọn template Cypher để truy xuất ngữ cảnh pháp lý cho "
        "câu hỏi về ĐIỀU KIỆN KẾT HÔN (Điều 8 và các điều liên quan).\n\n"
        "QUY TẮC ƯU TIÊN (theo thứ tự):\n"
        "1. Có đồng giới/cùng giới/hôn nhân đồng tính -> hon_nhan_cung_gioi_tinh "
        "(kể cả câu dùng từ cấm).\n"
        "2. Có phép tính tuổi, tuổi cụ thể, năm sinh hoặc đủ tuổi -> do_tuoi_ket_hon.\n"
        "3. Có quan hệ huyết thống, trực hệ, ba đời, cận huyết, cùng cha/mẹ, "
        "con riêng của bố, cháu cùng gốc -> quan_he_huyet_thong_va_ba_doi.\n"
        "4. Có đúng quan hệ cha/mẹ nuôi-con nuôi, cha chồng-con dâu, mẹ vợ-con rể, "
        "cha dượng-con riêng, mẹ kế-con riêng -> quan_he_nuoi_duong_va_thong_gia_bi_cam.\n"
        "5. Có em trai chồng-em gái vợ, em chồng-anh vợ hoặc thông gia không huyết thống "
        "-> quan_he_thong_gia_khong_huyet_thong.\n"
        "6. Có đám cưới/lễ cưới/công nhận là vợ chồng/vợ chồng hợp pháp "
        "-> xac_lap_quan_he_vo_chong_hop_phap (KHÔNG chọn dang_ky_ket_hon).\n"
        "7. Có án treo, án tích, bại liệt, khuyết tật hoặc mất năng lực hành vi "
        "-> anh_huong_tinh_trang_ca_nhan.\n"
        "8. Có khác tín ngưỡng, gia đình phản đối, hộ khẩu sau ly hôn, "
        "giáo viên-học sinh, xung khắc tuổi -> yeu_to_xa_hoi_khong_phai_tro_ngai.\n"
        "9. Có trường hợp nào bị cấm/liệt kê điều cấm mà không nêu quan hệ cụ thể "
        "-> cac_truong_hop_cam_ket_hon.\n"
        "10. Câu chỉ hỏi điều kiện/khái niệm chung -> dieu_kien_ket_hon_tong_quat.\n"
        "11. Mặc định 1 template/câu; tối đa 2 khi có hai yêu cầu pháp lý độc lập.\n"
        "12. KHÔNG bịa template name ngoài danh sách; fallback dieu_kien_ket_hon_tong_quat.\n"
        + "".join(lines)
    )


def _safety_net_classify(query: str, choices: List[TemplateChoice]) -> List[TemplateChoice]:
    q = query.lower()
    names = {c.template_name for c in choices}

    if re.search(r"đồng giới|cùng giới|đồng tính|hai nam|hai nữ", q):
        if "hon_nhan_cung_gioi_tinh" not in names:
            choices = [
                TemplateChoice(
                    template_name="hon_nhan_cung_gioi_tinh",
                    reason="Safety-net: cùng giới",
                )
            ] + choices

    if re.search(
        r"cận huyết|ba đời|trực hệ|cùng cha|cùng mẹ|con riêng của bố|"
        r"chung ông|chung bà|cùng một gốc",
        q,
    ):
        if not any(
            c.template_name == "quan_he_huyet_thong_va_ba_doi" for c in choices
        ):
            choices = [
                TemplateChoice(
                    template_name="quan_he_huyet_thong_va_ba_doi",
                    reason="Safety-net: quan hệ huyết thống/ba đời",
                )
            ] + choices

    if re.search(
        r"cha dượng.*con riêng|mẹ kế.*con riêng|cha chồng.*con dâu|"
        r"mẹ vợ.*con rể|cha mẹ nuôi.*con nuôi",
        q,
    ):
        if "quan_he_nuoi_duong_va_thong_gia_bi_cam" not in names:
            choices = [
                TemplateChoice(
                    template_name="quan_he_nuoi_duong_va_thong_gia_bi_cam",
                    reason="Safety-net: quan hệ bị cấm đích danh",
                )
            ] + choices

    if re.search(
        r"đám cưới|lễ cưới|công nhận.*vợ chồng|vợ chồng hợp pháp",
        q,
    ):
        if "xac_lap_quan_he_vo_chong_hop_phap" not in names:
            choices = [
                TemplateChoice(
                    template_name="xac_lap_quan_he_vo_chong_hop_phap",
                    reason="Safety-net: xác lập vợ chồng hợp pháp",
                )
            ] + choices

    if re.search(r"em trai chồng.*em gái vợ|em chồng.*anh vợ", q):
        if "quan_he_thong_gia_khong_huyet_thong" not in names:
            choices = [
                TemplateChoice(
                    template_name="quan_he_thong_gia_khong_huyet_thong",
                    reason="Safety-net: thông gia không huyết thống",
                )
            ] + choices

    valid_names = set(DIEU_KIEN_KET_HON_REGISTRY.names())
    choices = [c for c in choices if c.template_name in valid_names]
    if not choices:
        choices = [
            TemplateChoice(
                template_name="dieu_kien_ket_hon_tong_quat",
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
        print(f"[Classifier-dieu_kien_ket_hon] Lỗi: {exc}. Fallback tổng quát.")
        return [
            TemplateChoice(
                template_name="dieu_kien_ket_hon_tong_quat",
                reason="Fallback do lỗi LLM",
            )
        ]

    valid_names = set(DIEU_KIEN_KET_HON_REGISTRY.names())
    valid = [c for c in result.choices if c.template_name in valid_names]
    if not valid and result.choices:
        bad = [c.template_name for c in result.choices]
        print(f"[Classifier-dieu_kien_ket_hon] Template không hợp lệ: {bad}. Fallback.")
        valid = [
            TemplateChoice(
                template_name="dieu_kien_ket_hon_tong_quat",
                reason="Fallback template không hợp lệ",
            )
        ]
    if not valid:
        valid = [
            TemplateChoice(
                template_name="dieu_kien_ket_hon_tong_quat",
                reason="Fallback mặc định",
            )
        ]
    valid = _safety_net_classify(query, valid)
    print(
        f"[Classifier-dieu_kien_ket_hon] Chọn: "
        f"{[(c.template_name, c.reason) for c in valid]}"
    )
    return valid[:2]


_EXTRACT_SYS_PROMPT_BASE = (
    "Bạn là chuyên gia trích xuất tham số cho câu Cypher truy xuất luật pháp "
    "về điều kiện kết hôn. Điền chính xác các trường schema `{schema_name}`.\n\n"
    "QUY TẮC:\n"
    "1. ĐỌC description từng field — có bảng map ngữ thông tục → enum chuẩn.\n"
    "2. Không suy luận được → chọn giá trị mặc định an toàn (khong_ro, tong_quat).\n"
    "3. KHÔNG bịa enum ngoài Literal.\n"
    "4. Học sinh không được tự map thành chưa đủ 18 tuổi nếu câu không nêu tuổi.\n"
    "5. Bại liệt/khuyết tật không được map thành mất năng lực hành vi dân sự.\n"
    "6. `thoi_diem_su_kien`: mốc thời gian sự kiện 'YYYY-MM-DD' hoặc null nếu "
    "câu hỏi không nêu ngày/tháng/năm cụ thể. Nếu chỉ nêu năm (vd 2026) → '2026-12-31'."
)

_ENUM_FIELDS = {
    "gioi_tinh_hai_ben",
    "khia_canh_cung_gioi",
    "gioi_tinh_nguoi_can_xet",
    "dang_du_lieu_tuoi",
    "khia_canh_tuoi",
    "pham_vi_liet_ke",
    "khia_canh_cam",
    "loai_quan_he_huyet_thong",
    "khia_canh_ba_doi",
    "co_chung_goc_sinh_ra",
    "loai_quan_he_bi_cam",
    "khia_canh_quan_he_bi_cam",
    "loai_quan_he_thong_gia",
    "co_quan_he_huyet_thong_thuc_te",
    "khia_canh_thong_gia",
    "tinh_trang_dang_ky",
    "khia_canh_xac_lap",
    "hoan_canh_ca_nhan",
    "tinh_trang_nang_luc_hanh_vi",
    "khia_canh_anh_huong",
    "yeu_to_xa_hoi",
    "tinh_trang_hon_nhan_hien_tai",
    "co_du_tuoi_ro_rang",
    "khia_canh_yeu_to_xa_hoi",
    "khia_canh_tong_quat",
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


async def dieu_kien_ket_hon(query: str) -> dict[str, Any]:
    """3 bước: classify → extract → execute → normalize."""
    print(f"[Agent dieu_kien_ket_hon] Đang xử lý: '{query}'...")

    choices = await _classify_templates(query)

    templates: List[CypherTemplate] = []
    extract_tasks = []
    for choice in choices:
        template = DIEU_KIEN_KET_HON_REGISTRY.get(choice.template_name)
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
                    retriever_name="dieu_kien_ket_hon",
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
                "topic": "dieu_kien_ket_hon",
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
