"""Retriever cho chủ đề đại diện và trách nhiệm vợ chồng — Đ24-27 Luật HNGD 2014.

Pipeline 3 bước:
    1. CLASSIFY  -> LLM chọn 1-2 template (registry dai_dien_trach_nhiem_vo_chong).
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
from adapter.cypher_templates.dai_dien_trach_nhiem_vo_chong import (
    DAI_DIEN_TRACH_NHIEM_VO_CHONG_REGISTRY,
)
from adapter.cypher_templates.dai_dien_trach_nhiem_vo_chong.term_mapping import (
    resolve_term,
)
from adapter.cypher_templates.extract_schema import (
    build_params_with_date_schema,
    split_params_and_date,
)
from adapter.graph_viz import save_lazy_viz_stub
from application.legal_context import encode_context_record


dai_dien_trach_nhiem_vo_chong_description = {
    "type": "function",
    "function": {
        "name": "dai_dien_trach_nhiem_vo_chong",
        "description": (
            "Tra cứu đại diện và trách nhiệm của vợ chồng theo Điều 24-27 Luật HNGD 2014: "
            "căn cứ xác lập đại diện, ủy quyền giao dịch, đại diện khi mất/hạn chế năng lực, "
            "kinh doanh chung, GCN một tên, hiệu lực giao dịch trái đại diện, trách nhiệm liên đới và nợ."
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
    descriptions = DAI_DIEN_TRACH_NHIEM_VO_CHONG_REGISTRY.descriptions()
    lines = ["Các template Cypher cho chủ đề 'Đại diện và trách nhiệm vợ chồng':\n"]
    for name, desc in descriptions.items():
        lines.append(f"\n- **{name}**:\n{desc}\n")
    return (
        "Bạn là router chọn template Cypher để truy xuất ngữ cảnh pháp lý cho "
        "câu hỏi về ĐẠI DIỆN VÀ TRÁCH NHIỆM VỢ CHỒNG (Điều 24-27 Luật HNGD 2014).\n\n"
        "QUY TẮC ƯU TIÊN (theo thứ tự):\n"
        "1. Có 'vô hiệu', 'hiệu lực', 'ngay tình', 'mọi trường hợp', 'có ngoại lệ' "
        "cùng bối cảnh một bên tự giao dịch tài sản chung/GCN một tên "
        "-> hieu_luc_giao_dich_trai_dai_dien.\n"
        "2. Có 'sổ đỏ', 'sổ hồng', 'giấy chứng nhận', 'chỉ đứng tên', 'ghi tên vợ/chồng' "
        "nhưng KHÔNG hỏi hậu quả vô hiệu/ngay tình -> dai_dien_tai_san_chung_gcn_mot_ben.\n"
        "3. Có 'mất năng lực', 'hạn chế năng lực', 'giám hộ', 'Tòa án chỉ định', "
        "'ai đại diện trong vụ ly hôn' (khi bên kia mất/hạn chế năng lực) "
        "-> dai_dien_khi_nang_luc_hanh_vi_bi_anh_huong.\n"
        "4. Có 'đưa tài sản chung vào kinh doanh', 'thỏa thuận bằng lời nói/văn bản' "
        "-> dua_tai_san_chung_vao_kinh_doanh.\n"
        "5. Có 'kinh doanh chung', 'quan hệ kinh doanh', 'ký hợp đồng hàng hóa', "
        "'thỏa thuận người đại diện' (không hỏi đưa tài sản vào kinh doanh) "
        "-> dai_dien_trong_quan_he_kinh_doanh.\n"
        "6. Có 'ủy quyền', 'phải có sự đồng ý của cả hai', 'một mình ký', 'không đồng ý' "
        "và không có tín hiệu GCN/hiệu lực -> uy_quyen_giao_dich_can_dong_y.\n"
        "7. Có 'nợ', 'vay', 'trả nợ', 'nghĩa vụ', 'trách nhiệm liên đới', 'ngân hàng', "
        "'chủ nợ', 'sau ly hôn' (bối cảnh nợ, không phải đại diện mất năng lực) "
        "-> trach_nhiem_lien_doi_vo_chong.\n"
        "8. Có 'căn cứ xác lập đại diện', 'theo quy định pháp luật nào', hoặc hỏi tổng quát "
        "xác lập/thực hiện/chấm dứt giao dịch -> can_cu_xac_lap_dai_dien.\n"
        "9. Fallback -> can_cu_xac_lap_dai_dien; KHÔNG fallback sang template nợ.\n\n"
        "CHỐNG NHẦM:\n"
        "- 'tự bán nhà chung' + sổ một tên, không hỏi hiệu lực -> dai_dien_tai_san_chung_gcn_mot_ben.\n"
        "- Cùng câu nhưng có 'vô hiệu'/'ngay tình' -> hieu_luc_giao_dich_trai_dai_dien.\n"
        "- 'một mình ký bán nhà chung' không GCN -> uy_quyen_giao_dich_can_dong_y.\n"
        "- 'ly hôn' chỉ là bối cảnh nợ -> trach_nhiem_lien_doi_vo_chong, không template năng lực.\n"
        + "".join(lines)
    )


_ENUM_FIELDS = {
    "pham_vi_giao_dich",
    "co_uy_quyen_hoac_dong_y",
    "doi_tuong_giao_dich",
    "tinh_trang_nang_luc",
    "boi_canh",
    "can_cu_dai_dien",
    "boi_canh_kinh_doanh",
    "co_thoa_thuan_khac",
    "khia_canh",
    "hinh_thuc_thoa_thuan",
    "loai_giay_chung_nhan",
    "nguoi_dung_ten",
    "hanh_vi_giao_dich",
    "trong_tam_hau_qua",
    "tinh_trang_nguoi_thu_ba",
    "nhom_can_cu",
    "muc_dich_no",
    "thoi_diem_no",
    "tinh_trang_hon_nhan",
    "nguoi_thu_ba",
    "tai_san_thanh_toan",
}


def _safety_net_classify(query: str, choices: List[TemplateChoice]) -> List[TemplateChoice]:
    q = query.lower()
    names = {c.template_name for c in choices}
    valid_names = set(DAI_DIEN_TRACH_NHIEM_VO_CHONG_REGISTRY.names())

    has_hieu_luc = bool(
        re.search(r"vô hiệu|hiệu lực|ngay tình|mọi trường hợp|có ngoại lệ", q)
    )
    has_gcn = bool(
        re.search(
            r"sổ đỏ|sổ hồng|giấy chứng nhận|chỉ đứng tên|ghi tên vợ|ghi tên chồng|"
            r"chỉ ghi tên",
            q,
        )
    )
    has_no = bool(re.search(r"nợ|vay|trả nợ|nghĩa vụ|trách nhiệm liên đới|ngân hàng|chủ nợ", q))
    has_mat_han_che = bool(
        re.search(
            r"mất năng lực|hạn chế năng lực|giám hộ|tòa án chỉ định|"
            r"ai đại diện trong vụ ly hôn",
            q,
        )
    )

    if has_hieu_luc and has_gcn and "hieu_luc_giao_dich_trai_dai_dien" not in names:
        choices = [
            TemplateChoice(
                template_name="hieu_luc_giao_dich_trai_dai_dien",
                reason="Safety-net: hiệu lực/vô hiệu + GCN",
            )
        ] + choices
    elif has_gcn and not has_hieu_luc and "dai_dien_tai_san_chung_gcn_mot_ben" not in names:
        choices = [
            TemplateChoice(
                template_name="dai_dien_tai_san_chung_gcn_mot_ben",
                reason="Safety-net: GCN một tên",
            )
        ] + choices

    if has_mat_han_che and not has_no and "dai_dien_khi_nang_luc_hanh_vi_bi_anh_huong" not in names:
        choices = [
            TemplateChoice(
                template_name="dai_dien_khi_nang_luc_hanh_vi_bi_anh_huong",
                reason="Safety-net: năng lực hành vi",
            )
        ] + choices

    if re.search(r"đưa tài sản chung vào kinh doanh|thỏa thuận bằng lời nói|nói miệng", q):
        if "dua_tai_san_chung_vao_kinh_doanh" not in names:
            choices = [
                TemplateChoice(
                    template_name="dua_tai_san_chung_vao_kinh_doanh",
                    reason="Safety-net: đưa TS vào KD",
                )
            ] + choices

    if re.search(r"kinh doanh chung|làm ăn chung|ký hợp đồng.*hàng hóa", q):
        if (
            "dai_dien_trong_quan_he_kinh_doanh" not in names
            and "dua_tai_san_chung_vao_kinh_doanh" not in names
        ):
            choices = [
                TemplateChoice(
                    template_name="dai_dien_trong_quan_he_kinh_doanh",
                    reason="Safety-net: KD chung",
                )
            ] + choices

    if re.search(r"ủy quyền|phải có sự đồng ý của cả hai|một mình ký|không đồng ý", q):
        if (
            "uy_quyen_giao_dich_can_dong_y" not in names
            and not has_hieu_luc
            and not has_gcn
        ):
            choices = [
                TemplateChoice(
                    template_name="uy_quyen_giao_dich_can_dong_y",
                    reason="Safety-net: ủy quyền/đồng ý",
                )
            ] + choices

    if has_no and "trach_nhiem_lien_doi_vo_chong" not in names:
        choices = [
            TemplateChoice(
                template_name="trach_nhiem_lien_doi_vo_chong",
                reason="Safety-net: nợ/trách nhiệm",
            )
        ] + choices

    if re.search(r"căn cứ xác lập đại diện|theo quy định pháp luật nào", q):
        if "can_cu_xac_lap_dai_dien" not in names and not has_no:
            choices = [
                TemplateChoice(
                    template_name="can_cu_xac_lap_dai_dien",
                    reason="Safety-net: căn cứ đại diện",
                )
            ] + choices

    choices = [c for c in choices if c.template_name in valid_names]
    if not choices:
        choices = [
            TemplateChoice(
                template_name="can_cu_xac_lap_dai_dien",
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
        print(f"[Classifier-dai_dien] Lỗi: {exc}. Fallback.")
        return [
            TemplateChoice(
                template_name="can_cu_xac_lap_dai_dien",
                reason="Fallback do lỗi LLM",
            )
        ]

    valid_names = set(DAI_DIEN_TRACH_NHIEM_VO_CHONG_REGISTRY.names())
    valid = [c for c in result.choices if c.template_name in valid_names]
    if not valid and result.choices:
        bad = [c.template_name for c in result.choices]
        print(f"[Classifier-dai_dien] Template không hợp lệ: {bad}. Fallback.")
        valid = [
            TemplateChoice(
                template_name="can_cu_xac_lap_dai_dien",
                reason="Fallback template không hợp lệ",
            )
        ]
    if not valid:
        valid = [
            TemplateChoice(
                template_name="can_cu_xac_lap_dai_dien",
                reason="Fallback mặc định",
            )
        ]
    valid = _safety_net_classify(query, valid)
    print(f"[Classifier-dai_dien] Chọn: {[(c.template_name, c.reason) for c in valid]}")
    return valid[:2]


_EXTRACT_SYS_PROMPT_BASE = (
    "Bạn là chuyên gia trích xuất tham số cho câu Cypher truy xuất luật pháp "
    "về đại diện và trách nhiệm vợ chồng. Điền chính xác các trường schema `{schema_name}`.\n\n"
    "QUY TẮC:\n"
    "1. ĐỌC description từng field — có bảng map ngữ thông tục → enum chuẩn.\n"
    "2. Không suy luận được → chọn giá trị mặc định an toàn (khong_ro, tat_ca, tong_quat).\n"
    "3. KHÔNG bịa enum ngoài Literal.\n"
    "4. Câu đối chiếu nợ chung/riêng → nhom_can_cu='doi_chieu_chung_rieng'.\n"
    "5. `thoi_diem_su_kien`: mốc thời gian 'YYYY-MM-DD' hoặc null."
)


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


def _override_doi_chieu_chung_rieng(params: BaseModel, query: str) -> BaseModel:
    data = params.model_dump()
    if "nhom_can_cu" not in data:
        return params
    if data.get("nhom_can_cu") != "tong_quat":
        return params

    q = query.lower()
    cross_patterns = [
        ("nợ chung", "nợ riêng"),
        ("tài sản chung", "nợ riêng"),
        ("chung hay riêng", ""),
        ("vợ có phải trả nợ", ""),
        ("chồng có phải trả nợ", ""),
    ]
    should = any(
        (a in q and (not b or b in q)) for a, b in cross_patterns if a in q
    )
    if not should:
        return params

    data["nhom_can_cu"] = "doi_chieu_chung_rieng"
    if data.get("muc_dich_no") == "ca_nhan":
        data["muc_dich_no"] = "khong_ro"
    print("[cross-cutting] nhom_can_cu -> doi_chieu_chung_rieng")
    try:
        return params.__class__(**data)
    except Exception as exc:
        print(f"[cross-cutting] failed: {exc}")
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
    params = _override_doi_chieu_chung_rieng(params, query)
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


async def dai_dien_trach_nhiem_vo_chong(query: str) -> dict[str, Any]:
    """3 bước: classify → extract → execute → normalize."""
    print(f"[Agent dai_dien_trach_nhiem_vo_chong] Đang xử lý: '{query}'...")

    choices = await _classify_templates(query)

    templates: List[CypherTemplate] = []
    extract_tasks = []
    for choice in choices:
        template = DAI_DIEN_TRACH_NHIEM_VO_CHONG_REGISTRY.get(choice.template_name)
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
                    retriever_name="dai_dien_trach_nhiem_vo_chong",
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
                "topic": "dai_dien_trach_nhiem_vo_chong",
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
