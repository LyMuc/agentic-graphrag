"""Retriever cho chủ đề "Xử phạt vi phạm" — NĐ82 Đ58-63, NĐ282 Đ37-53, BLHS Đ181-187.

Pipeline 3 bước:
    1. CLASSIFY  -> LLM chọn 1-2 template (registry topic 'xu_phat_vi_pham').
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
from adapter.cypher_templates.xu_phat_vi_pham import XU_PHAT_VI_PHAM_REGISTRY
from adapter.cypher_templates.xu_phat_vi_pham.term_mapping import resolve_term
from adapter.graph_viz import save_lazy_viz_stub
from utils.utils import chuan_hoa_Context_cho_LLM


xu_phat_vi_pham_description = {
    "type": "function",
    "function": {
        "name": "xu_phat_vi_pham",
        "description": (
            "Tra cứu xử phạt vi phạm hành chính và/hoặc truy cứu trách nhiệm hình sự "
            "trong lĩnh vực hôn nhân gia đình: tảo hôn, một vợ một chồng, kết hôn/ly hôn, "
            "sinh con/mang thai hộ, giám hộ, nuôi con nuôi, bạo lực gia đình (NĐ82, NĐ282, BLHS)."
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
        description="Tên template — phải khớp 1 trong 29 template đã liệt kê."
    )
    reason: str = Field(description="Lý do ngắn (1 câu) chọn template này.")


class TemplateChoiceList(BaseModel):
    choices: List[TemplateChoice] = Field(
        description="Danh sách template phù hợp. Tối đa 2."
    )


def _build_classifier_prompt() -> str:
    descriptions = XU_PHAT_VI_PHAM_REGISTRY.descriptions()
    lines = ["Các template Cypher cho chủ đề 'Xử phạt vi phạm':\n"]
    for name, desc in descriptions.items():
        lines.append(f"\n- **{name}**:\n{desc}\n")
    return (
        "Bạn là router chọn template Cypher để truy xuất ngữ cảnh pháp lý cho "
        "câu hỏi về XỬ PHẠT VI PHẠM trong lĩnh vực hôn nhân gia đình.\n\n"
        "QUY TẮC ƯU TIÊN:\n"
        "1. Ưu tiên hành vi cụ thể; chỉ dùng xu_phat_ket_hon_ly_hon_tong_quat khi câu mơ hồ.\n"
        "1b. 'Hành vi bị cấm', 'Điều 5 khoản 2', 'pháp luật cấm gì' → hanh_vi_bi_cam_hngd_tong_quat; "
        "không dùng nếu câu chỉ hỏi mức phạt/TNHS và đã map rõ template xử phạt.\n"
        "2. 'Phạt tiền/phạt hành chính' → nhánh VPHC; 'truy cứu TNHS/phạt tù' → hình sự; "
        "không rõ → template kết hợp seed cả hai khi có loai_che_tai.\n"
        "3. Ngoại tình/một vợ một chồng → vi_pham_mot_vo_mot_chong; không chọn hình sự "
        "chỉ vì có từ 'ngoại tình'.\n"
        "4. Cản trở/cưỡng ép kết hôn/ly hôn, thách cưới → can_tro_cuong_ep_ket_hon_ly_hon.\n"
        "5. Kết hôn ba đời/cận huyết (VPHC) → quan_he_hon_nhan_bi_cam_vphc; "
        "tội loạn luân/giao cấu (HS) → toi_loan_luan_hinh_su.\n"
        "6. Câu mơ hồ 'cận huyết bị phạt thế nào' có thể chọn tối đa 2 template VPHC + HS.\n"
        "7. Tảo hôn/chưa đủ tuổi → tao_hon_va_to_chuc_tao_hon.\n"
        "8. Mang thai hộ lấy tiền → sinh_con_mang_thai_ho_thuong_mai (VPHC); "
        "tổ chức/môi giới → nhánh Đ187.\n"
        "9. Bạo lực gia đình: đánh đập Đ37 → bao_luc_the_chat_nguoc_dai; "
        "đuổi khỏi nhà Đ45 → cuong_ep_ra_khoi_cho_o; có thể chọn cả hai nếu độc lập.\n"
        "10. Ngăn thăm con → ngan_can_tham_nom_cham_soc; không cấp dưỡng → vi_pham_cap_duong_nuoi_duong.\n"
        "11. Chiếm tài sản vợ/chồng → bao_luc_kinh_te.\n"
        "12. Kết hôn/ly hôn giả → ket_hon_ly_hon_gia_tao.\n"
        "13. Mặc định 1 template/câu; tối đa 2 khi hai hành vi độc lập, cần ranh giới VPHC/HS, "
        "hoặc vừa hỏi bị cấm vừa hỏi xử phạt.\n"
        "14. KHÔNG bịa template name ngoài danh sách.\n"
        + "".join(lines)
    )


def _safety_net_classify(query: str, choices: List[TemplateChoice]) -> List[TemplateChoice]:
    q = query.lower()
    names = {c.template_name for c in choices}

    if re.search(r"điều 5 khoản 2|hành vi bị cấm|pháp luật cấm gì", q) and not re.search(
        r"phạt|mức phạt|truy cứu|tội|tnhs", q
    ):
        if "hanh_vi_bi_cam_hngd_tong_quat" not in names:
            choices = [
                TemplateChoice(
                    template_name="hanh_vi_bi_cam_hngd_tong_quat",
                    reason="Safety-net: hành vi bị cấm Điều 5 khoản 2",
                )
            ] + choices

    if re.search(r"ngoại tình|một vợ|một chồng|có bồ", q) and not re.search(
        r"loạn luân|giao cấu|cận huyết.*hình sự", q
    ):
        if not any(c.template_name == "vi_pham_mot_vo_mot_chong" for c in choices):
            choices = [
                TemplateChoice(
                    template_name="vi_pham_mot_vo_mot_chong",
                    reason="Safety-net: ngoại tình/một vợ một chồng",
                )
            ] + choices

    if re.search(r"đuổi.*(khỏi nhà|ra khỏi)|cưỡng ép.*(ra khỏi|rời).*nhà", q):
        if "cuong_ep_ra_khoi_cho_o" not in names:
            choices.append(
                TemplateChoice(
                    template_name="cuong_ep_ra_khoi_cho_o",
                    reason="Safety-net: đuổi/cưỡng ép ra khỏi chỗ ở",
                )
            )

    if re.search(r"đánh|đấm|hành hung|ngược đãi", q) and re.search(
        r"đuổi|ra khỏi nhà", q
    ):
        needed = {"bao_luc_the_chat_nguoc_dai", "cuong_ep_ra_khoi_cho_o"}
        if not needed.issubset(names):
            for tpl, reason in [
                ("bao_luc_the_chat_nguoc_dai", "Safety-net: đánh đập"),
                ("cuong_ep_ra_khoi_cho_o", "Safety-net: đuổi khỏi nhà"),
            ]:
                if tpl not in names:
                    choices.append(TemplateChoice(template_name=tpl, reason=reason))

    if re.search(r"cận huyết", q) and re.search(
        r"hình sự|truy cứu|tội|phạt tù", q
    ):
        if "toi_loan_luan_hinh_su" not in names:
            choices.append(
                TemplateChoice(
                    template_name="toi_loan_luan_hinh_su",
                    reason="Safety-net: cận huyết + hình sự",
                )
            )

    if re.search(r"cận huyết|ba đời|họ hàng gần", q) and re.search(
        r"phạt tiền|phạt hành chính|mức phạt", q
    ):
        if "quan_he_hon_nhan_bi_cam_vphc" not in names:
            choices.append(
                TemplateChoice(
                    template_name="quan_he_hon_nhan_bi_cam_vphc",
                    reason="Safety-net: quan hệ bị cấm VPHC",
                )
            )

    if re.search(r"không (gửi|cấp).*dưỡng|trốn.*cấp dưỡng", q):
        if "vi_pham_cap_duong_nuoi_duong" not in names:
            choices = [
                TemplateChoice(
                    template_name="vi_pham_cap_duong_nuoi_duong",
                    reason="Safety-net: cấp dưỡng/nuôi dưỡng",
                )
            ] + choices

    if re.search(r"cản trở|cưỡng ép|thách cưới|ép ly hôn|ép cưới", q):
        if "can_tro_cuong_ep_ket_hon_ly_hon" not in names:
            choices = [
                TemplateChoice(
                    template_name="can_tro_cuong_ep_ket_hon_ly_hon",
                    reason="Safety-net: cản trở/cưỡng ép kết hôn/ly hôn",
                )
            ] + choices

    deduped: list[TemplateChoice] = []
    seen: set[str] = set()
    for c in choices:
        if c.template_name not in seen:
            seen.add(c.template_name)
            deduped.append(c)
    return deduped[:2]


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
        print(f"[Classifier-xu_phat_vi_pham] Lỗi: {exc}. Fallback tổng quát.")
        return [
            TemplateChoice(
                template_name="xu_phat_ket_hon_ly_hon_tong_quat",
                reason="Fallback do lỗi LLM",
            )
        ]

    valid_names = set(XU_PHAT_VI_PHAM_REGISTRY.names())
    valid = [c for c in result.choices if c.template_name in valid_names]
    if not valid:
        valid = [
            TemplateChoice(
                template_name="xu_phat_ket_hon_ly_hon_tong_quat",
                reason="Fallback template không hợp lệ hoặc rỗng",
            )
        ]
    valid = _safety_net_classify(query, valid)
    print(
        f"[Classifier-xu_phat_vi_pham] Chọn: "
        f"{[(c.template_name, c.reason) for c in valid]}"
    )
    return valid[:2]


_EXTRACT_SYS_PROMPT_BASE = (
    "Bạn là chuyên gia trích xuất tham số cho câu Cypher truy xuất luật pháp "
    "về xử phạt vi phạm hôn nhân gia đình. Điền chính xác các trường schema `{schema_name}`.\n\n"
    "QUY TẮC:\n"
    "1. ĐỌC description từng field — có bảng map ngữ thông tục → enum chuẩn.\n"
    "2. Không suy luận được → chọn giá trị mặc định an toàn (khong_ro, tong_quat).\n"
    "3. KHÔNG bịa enum ngoài Literal.\n"
    "4. 'Phạt tiền/mức phạt' → loai_che_tai=vphc, khia_canh_che_tai=muc_phat.\n"
    "5. 'Truy cứu TNHS/phạt tù' → loai_che_tai=hinh_su.\n"
    "6. 'Ngoại tình' đơn thuần KHÔNG đủ để chọn hinh_su.\n"
    "7. `thoi_diem_su_kien`: 'YYYY-MM-DD' hoặc null; chỉ nêu năm → 'YYYY-12-31'."
)

_ENUM_FIELDS = {
    "loai_che_tai",
    "khia_canh_che_tai",
    "pham_vi",
    "dang_hanh_vi",
    "hau_qua_hinh_su",
    "moi_quan_he",
    "dang_quan_he",
    "co_hanh_vi_giao_cau",
    "dang_gia_tao",
    "muc_dich",
    "quan_he_cap_duong",
    "dang_nghia_vu",
    "muc_do",
    "quan_he",
    "dang_quyen",
    "loai_tai_san",
    "doi_tuong_dac_biet",
    "doi_tuong",
    "vai_tro",
    "dang_noi_dung",
    "tinh_trang_dang_ky",
    "dang_vi_pham",
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


async def xu_phat_vi_pham(query: str) -> dict[str, Any]:
    """3 bước: classify → extract → execute → normalize."""
    print(f"[Agent xu_phat_vi_pham] Đang xử lý: '{query}'...")

    choices = await _classify_templates(query)

    templates: List[CypherTemplate] = []
    extract_tasks = []
    for choice in choices:
        template = XU_PHAT_VI_PHAM_REGISTRY.get(choice.template_name)
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
                "topic": "xu_phat_vi_pham",
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
