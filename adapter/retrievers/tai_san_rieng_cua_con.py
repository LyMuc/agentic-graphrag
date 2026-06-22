"""Retriever cho chủ đề tài sản riêng của con — Đ75-77 Luật HNGD 2014.

Pipeline 3 bước:
    1. CLASSIFY  -> LLM chọn 1+ template (registry topic 'tai_san_rieng_cua_con').
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
from adapter.cypher_templates.tai_san_rieng_cua_con import TAI_SAN_RIENG_CUA_CON_REGISTRY
from adapter.cypher_templates.tai_san_rieng_cua_con.term_mapping import resolve_term
from adapter.graph_viz import save_lazy_viz_stub
from application.legal_context import encode_context_record


tai_san_rieng_cua_con_description = {
    "type": "function",
    "function": {
        "name": "tai_san_rieng_cua_con",
        "description": (
            "Tra cứu quyền có tài sản riêng của con, thành phần tài sản riêng (thừa kế, tặng cho, "
            "thu nhập lao động, hoa lợi/lợi tức); nghĩa vụ đóng góp thu nhập; quyền tự quản lý hoặc "
            "nhờ cha mẹ quản lý; cha mẹ quản lý/ủy quyền/giao lại; trường hợp cha mẹ không quản lý; "
            "định đoạt tài sản con dưới 15 tuổi, từ 15-17 tuổi, hoặc con đã thành niên mất năng lực."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Câu hỏi cụ thể về tài sản riêng, quản lý hoặc định đoạt tài sản của con.",
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
    descriptions = TAI_SAN_RIENG_CUA_CON_REGISTRY.descriptions()
    lines = ["Các template Cypher cho chủ đề 'Tài sản riêng của con':\n"]
    for name, desc in descriptions.items():
        lines.append(f"\n- **{name}**:\n{desc}\n")
    return (
        "Bạn là router chọn template Cypher để truy xuất ngữ cảnh pháp lý cho "
        "câu hỏi về TÀI SẢN RIÊNG CỦA CON (Điều 75-77 Luật HNGD 2014).\n\n"
        "QUY TẮC ƯU TIÊN (theo thứ tự):\n"
        "1. Có định đoạt/bán/chuyển nhượng/dùng tài sản kinh doanh/mở quán -> nhóm định đoạt, "
        "KHÔNG chọn template quản lý.\n"
        "2. Nhóm định đoạt + đã thành niên + mất năng lực hành vi dân sự -> "
        "dinh_doat_tai_san_con_thanh_nien_mat_nang_luc.\n"
        "3. Nhóm định đoạt + con 15-17 tuổi hoặc bất động sản/xe đăng ký/kinh doanh trong bối cảnh "
        "15-17 tuổi -> dinh_doat_tai_san_con_tu_du_15_den_duoi_18_tuoi.\n"
        "4. Nhóm định đoạt + dưới 15 tuổi, tuổi 9-14, nguyện vọng từ 9 tuổi, cha mẹ/người giám hộ "
        "đang quản lý -> dinh_doat_tai_san_con_duoi_15_tuoi.\n"
        "5. Có quản lý + con đang được người khác giám hộ hoặc người tặng cho/di chúc chỉ định "
        "-> cha_me_khong_quan_ly_hoac_chuyen_giao_cho_nguoi_khac (K3 trừ khi câu nêu đủ chuỗi "
        "cha mẹ đang quản lý -> con đã thành niên mất năng lực -> giao người giám hộ thì K4).\n"
        "6. Có quản lý + dưới 15/mất năng lực/ủy quyền/giao lại/khôi phục năng lực/thỏa thuận khác "
        "-> quan_ly_tai_san_con_duoi_15_hoac_mat_nang_luc.\n"
        "7. Có tự quản lý hoặc nhờ cha mẹ quản lý + con từ đủ 15 tuổi "
        "-> quan_ly_tai_san_con_tu_du_15_tuoi.\n"
        "8. Có đóng góp/chăm lo đời sống chung/nhu cầu thiết yếu/chi tiêu gia đình "
        "-> nghia_vu_dong_gop_thu_nhap_cua_con.\n"
        "9. Có tài sản riêng gồm/thừa kế/tặng cho/thu nhập lao động/hoa lợi/hình thành từ tài sản riêng "
        "-> xac_dinh_tai_san_rieng_cua_con.\n"
        "10. Fallback topic -> xac_dinh_tai_san_rieng_cua_con với params broad.\n"
        "11. Mặc định 1 template/câu; tối đa 2 khi có hai yêu cầu pháp lý độc lập.\n"
        "12. Phân biệt quản lý (Đ76) và định đoạt (Đ77); không route chỉ theo từ xe/đất.\n"
        + "".join(lines)
    )


def _safety_net_classify(query: str, choices: List[TemplateChoice]) -> List[TemplateChoice]:
    q = query.lower()
    names = {c.template_name for c in choices}
    valid_names = set(TAI_SAN_RIENG_CUA_CON_REGISTRY.names())

    is_dinh_doat = bool(
        re.search(
            r"định đoạt|\bbán\b|chuyển nhượng|dùng tài sản.*kinh doanh|mở quán|góp vốn",
            q,
        )
    )
    is_quan_ly = "quản lý" in q and not is_dinh_doat

    if is_dinh_doat:
        if re.search(r"đã thành niên.*mất năng lực|mất năng lực.*đã thành niên", q):
            if "dinh_doat_tai_san_con_thanh_nien_mat_nang_luc" not in names:
                choices = [
                    TemplateChoice(
                        template_name="dinh_doat_tai_san_con_thanh_nien_mat_nang_luc",
                        reason="Safety-net: định đoạt con đã thành niên mất năng lực",
                    )
                ] + choices
        elif re.search(
            r"\b1[5-7]\s*tuổi|từ đủ 15|15.*17|chưa đủ 18|"
            r"chuyển nhượng.*đất|bán.*xe|đăng ký|kinh doanh|mở quán",
            q,
        ):
            if "dinh_doat_tai_san_con_tu_du_15_den_duoi_18_tuoi" not in names:
                choices = [
                    TemplateChoice(
                        template_name="dinh_doat_tai_san_con_tu_du_15_den_duoi_18_tuoi",
                        reason="Safety-net: định đoạt 15-17 tuổi hoặc ngoại lệ Đ77 k2",
                    )
                ] + choices
        elif re.search(
            r"dưới 15|chưa đủ 15|nguyện vọng|từ đủ 9|\b9 tuổi|\b10 tuổi",
            q,
        ):
            if "dinh_doat_tai_san_con_duoi_15_tuoi" not in names:
                choices = [
                    TemplateChoice(
                        template_name="dinh_doat_tai_san_con_duoi_15_tuoi",
                        reason="Safety-net: định đoạt con dưới 15 tuổi",
                    )
                ] + choices

    if is_quan_ly:
        if re.search(
            r"giám hộ|ông bà giám hộ|người tặng cho.*chỉ định|di chúc.*chỉ định|"
            r"không phải quản lý|ai quản lý.*giám hộ",
            q,
        ):
            if "cha_me_khong_quan_ly_hoac_chuyen_giao_cho_nguoi_khac" not in names:
                choices = [
                    TemplateChoice(
                        template_name="cha_me_khong_quan_ly_hoac_chuyen_giao_cho_nguoi_khac",
                        reason="Safety-net: cha mẹ không quản lý / người khác quản lý",
                    )
                ] + choices
        elif re.search(
            r"dưới 15|chưa đủ 15|mất năng lực|ủy quyền|giao lại|khôi phục năng lực|thỏa thuận",
            q,
        ):
            if "quan_ly_tai_san_con_duoi_15_hoac_mat_nang_luc" not in names:
                choices = [
                    TemplateChoice(
                        template_name="quan_ly_tai_san_con_duoi_15_hoac_mat_nang_luc",
                        reason="Safety-net: quản lý Đ76 k2",
                    )
                ] + choices
        elif re.search(r"tự quản lý|nhờ cha mẹ|từ đủ 15|\b1[5-7]\s*tuổi", q):
            if "quan_ly_tai_san_con_tu_du_15_tuoi" not in names:
                choices = [
                    TemplateChoice(
                        template_name="quan_ly_tai_san_con_tu_du_15_tuoi",
                        reason="Safety-net: tự quản lý/nhờ cha mẹ Đ76 k1",
                    )
                ] + choices

    if re.search(r"đóng góp|chăm lo đời sống|nhu cầu thiết yếu|chi tiêu gia đình", q):
        if "nghia_vu_dong_gop_thu_nhap_cua_con" not in names:
            choices = [
                TemplateChoice(
                    template_name="nghia_vu_dong_gop_thu_nhap_cua_con",
                    reason="Safety-net: nghĩa vụ đóng góp Đ75 k2-k3",
                )
            ] + choices

    if re.search(
        r"mất năng lực.*ai quản lý|ai quản lý.*mất năng lực",
        q,
    ) and not is_dinh_doat:
        if "quan_ly_tai_san_con_duoi_15_hoac_mat_nang_luc" not in names:
            choices = [
                TemplateChoice(
                    template_name="quan_ly_tai_san_con_duoi_15_hoac_mat_nang_luc",
                    reason="Safety-net: quản lý khi mất năng lực (Đ76 k2)",
                )
            ] + choices

    choices = [c for c in choices if c.template_name in valid_names]
    if not choices:
        choices = [
            TemplateChoice(
                template_name="xac_dinh_tai_san_rieng_cua_con",
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
        print(f"[Classifier-tai_san_rieng_cua_con] Lỗi: {exc}. Fallback tổng quát.")
        return [
            TemplateChoice(
                template_name="xac_dinh_tai_san_rieng_cua_con",
                reason="Fallback do lỗi LLM",
            )
        ]

    valid_names = set(TAI_SAN_RIENG_CUA_CON_REGISTRY.names())
    valid = [c for c in result.choices if c.template_name in valid_names]
    if not valid and result.choices:
        bad = [c.template_name for c in result.choices]
        print(f"[Classifier-tai_san_rieng_cua_con] Template không hợp lệ: {bad}. Fallback.")
        valid = [
            TemplateChoice(
                template_name="xac_dinh_tai_san_rieng_cua_con",
                reason="Fallback template không hợp lệ",
            )
        ]
    if not valid:
        valid = [
            TemplateChoice(
                template_name="xac_dinh_tai_san_rieng_cua_con",
                reason="Fallback mặc định",
            )
        ]
    valid = _safety_net_classify(query, valid)
    print(
        f"[Classifier-tai_san_rieng_cua_con] Chọn: "
        f"{[(c.template_name, c.reason) for c in valid]}"
    )
    return valid[:2]


_EXTRACT_SYS_PROMPT_BASE = (
    "Bạn là chuyên gia trích xuất tham số cho câu Cypher truy xuất luật pháp "
    "về tài sản riêng của con (Đ75-77). Điền chính xác các trường schema `{schema_name}`.\n\n"
    "QUY TẮC:\n"
    "1. ĐỌC description từng field — map ngữ thông tục → enum chuẩn.\n"
    "2. Không suy luận được → chọn giá trị mặc định an toàn (khong_ro, tong_quat).\n"
    "3. KHÔNG bịa enum ngoài Literal.\n"
    "4. Phân biệt quản lý (Đ76) và định đoạt (Đ77).\n"
    "5. 'Đã thành niên mất năng lực' là một cụm — không chỉ map thành da_thanh_nien.\n"
    "6. Không tự suy co_thu_nhap=co chỉ vì con từ 15 tuổi.\n"
    "7. `thoi_diem_su_kien`: 'YYYY-MM-DD' hoặc null; chỉ nêu năm → 'YYYY-12-31'."
)

_ENUM_FIELDS = {
    "khia_canh_tai_san",
    "loai_tai_san",
    "nhom_tuoi",
    "song_chung_voi_cha_me",
    "co_thu_nhap",
    "khia_canh_dong_gop",
    "lua_chon_quan_ly",
    "khia_canh_quan_ly",
    "tinh_trang_con",
    "truong_hop_quan_ly",
    "nguoi_dang_quan_ly",
    "nguoi_thuc_hien",
    "khia_canh_dinh_doat",
    "hinh_thuc_dinh_doat",
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


async def tai_san_rieng_cua_con(query: str) -> dict[str, Any]:
    """3 bước: classify → extract → execute → normalize."""
    print(f"[Agent tai_san_rieng_cua_con] Đang xử lý: '{query}'...")

    choices = await _classify_templates(query)

    templates: List[CypherTemplate] = []
    extract_tasks = []
    for choice in choices:
        template = TAI_SAN_RIENG_CUA_CON_REGISTRY.get(choice.template_name)
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
                    retriever_name="tai_san_rieng_cua_con",
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
                "topic": "tai_san_rieng_cua_con",
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
