"""Retriever cho chủ đề xác định cha, mẹ, con — Đ88-93, 99, 101-102 Luật HNGD 2014.

Pipeline 3 bước:
    1. CLASSIFY  -> LLM chọn template (registry topic 'xac_dinh_cha_me_con').
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
from adapter.cypher_templates.xac_dinh_cha_me_con import XAC_DINH_CHA_ME_CON_REGISTRY
from adapter.cypher_templates.xac_dinh_cha_me_con.term_mapping import resolve_term
from adapter.graph_viz import save_lazy_viz_stub
from utils.utils import chuan_hoa_Context_cho_LLM


xac_dinh_cha_me_con_description = {
    "type": "function",
    "function": {
        "name": "xac_dinh_cha_me_con",
        "description": (
            "Tra cứu quy định XÁC ĐỊNH QUAN HỆ CHA, MẸ, CON: con chung theo hôn nhân (Đ88), "
            "yêu cầu Tòa án xác định là/không phải con (Đ89), quyền nhận cha/mẹ/con (Đ90-91), "
            "người yêu cầu đã chết (Đ92), hỗ trợ sinh sản/mang thai hộ (Đ93, 99), "
            "thẩm quyền và người có quyền yêu cầu (Đ101-102). "
            "Không dùng cho quyền nuôi con sau ly hôn hay quyền nghĩa vụ cha mẹ con hàng ngày."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Câu hỏi cụ thể về xác định quan hệ cha, mẹ, con.",
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
    descriptions = XAC_DINH_CHA_ME_CON_REGISTRY.descriptions()
    lines = ["Các template Cypher cho chủ đề 'Xác định cha, mẹ, con':\n"]
    for name, desc in descriptions.items():
        lines.append(f"\n- **{name}**:\n{desc}\n")
    return (
        "Bạn là router chọn template Cypher để truy xuất ngữ cảnh pháp lý cho "
        "câu hỏi về XÁC ĐỊNH QUAN HỆ CHA, MẸ, CON (Điều 88-93, 99, 101-102 Luật HNGD 2014).\n\n"
        "QUY TẮC ƯU TIÊN (theo thứ tự):\n"
        "1. 'ai/cơ quan nào có thẩm quyền', 'Tòa án hay hộ tịch', 'UBND hay Tòa án' "
        "và trọng tâm là NƠI GIẢI QUYẾT → tham_quyen_xac_dinh_cha_me_con.\n"
        "2. 'ai/người nào/cơ quan X có quyền yêu cầu', 'người giám hộ', "
        "'Hội Liên hiệp Phụ nữ' và trọng tâm là CHỦ THỂ YÊU CẦU "
        "→ nguoi_co_quyen_yeu_cau_xac_dinh_cha_me_con.\n"
        "3. 'tranh chấp' + hỗ trợ sinh sản/IVF/mang thai hộ, hoặc chưa giao trẻ và bên nhờ "
        "cùng chết/mất năng lực → giai_quyet_tranh_chap_ho_tro_sinh_san_mang_thai_ho.\n"
        "4. IVF, kỹ thuật hỗ trợ sinh sản, phụ nữ độc thân, người cho tinh trùng/noãn/phôi, "
        "mang thai hộ nhân đạo → xac_dinh_cha_me_bang_ho_tro_sinh_san.\n"
        "5. 'người có yêu cầu đã chết', 'người thân/gia đình yêu cầu thay' "
        "→ xac_dinh_khi_nguoi_yeu_cau_da_chet.\n"
        "6. 'nhận cha', 'nhận mẹ', 'nhận con', sự đồng ý cha/mẹ/vợ/chồng, "
        "người được nhận đã chết → quyen_nhan_cha_me_con.\n"
        "7. 'khởi kiện xác định là con/không phải con', khai sinh ghi người khác, "
        "đang/chưa được ghi nhận là cha mẹ, ADN phủ định quan hệ "
        "→ yeu_cau_xac_dinh_con_tai_toa_an.\n"
        "8. Sinh/có thai trong hôn nhân, 300 ngày sau chấm dứt hôn nhân, sinh trước đăng ký "
        "kết hôn được thừa nhận, cha mẹ phủ nhận con → xac_dinh_con_chung_theo_hon_nhan.\n"
        "9. Câu vừa hỏi 'ai có quyền' vừa 'cơ quan nào': ưu tiên theo danh từ chính — "
        "'ai/người nào' → Đ102; 'cơ quan/thẩm quyền' → Đ101.\n"
        "10. Mặc định 1 template/câu; tối đa 2 khi có hai yêu cầu pháp lý độc lập.\n"
        "11. KHÔNG seed cứng toàn bộ Điều 88-93, 99, 101-102.\n"
        + "".join(lines)
    )


def _fallback_by_keywords(query: str) -> str:
    q = query.lower()
    if re.search(
        r"thẩm quyền|cơ quan nào|ubnd hay tòa|tòa án hay hộ tịch|hộ tịch hay tòa",
        q,
    ):
        return "tham_quyen_xac_dinh_cha_me_con"
    if re.search(
        r"ai có quyền yêu cầu|người giám hộ|hội liên hiệp phụ nữ|"
        r"cơ quan quản lý.*gia đình|cơ quan quản lý.*trẻ em",
        q,
    ):
        return "nguoi_co_quyen_yeu_cau_xac_dinh_cha_me_con"
    if re.search(r"ivf|hỗ trợ sinh sản|mang thai hộ|tinh trùng|noãn|phôi", q):
        if re.search(r"tranh chấp|chưa giao|giám hộ|cấp dưỡng|không nhận nuôi", q):
            return "giai_quyet_tranh_chap_ho_tro_sinh_san_mang_thai_ho"
        return "xac_dinh_cha_me_bang_ho_tro_sinh_san"
    if re.search(r"người.*đã chết|yêu cầu thay|người thân.*yêu cầu", q):
        return "xac_dinh_khi_nguoi_yeu_cau_da_chet"
    if re.search(r"nhận cha|nhận mẹ|nhận con|đồng ý.*vợ|đồng ý.*chồng", q):
        return "quyen_nhan_cha_me_con"
    if re.search(r"adn|khai sinh|không phải con|xác định.*là con|khởi kiện", q):
        return "yeu_cau_xac_dinh_con_tai_toa_an"
    if re.search(
        r"300 ngày|con chung|phủ nhận con|không thừa nhận|sinh trong.*hôn nhân|"
        r"có thai.*kết hôn",
        q,
    ):
        return "xac_dinh_con_chung_theo_hon_nhan"
    return "xac_dinh_con_chung_theo_hon_nhan"


def _safety_net_classify(query: str, choices: List[TemplateChoice]) -> List[TemplateChoice]:
    q = query.lower()
    names = {c.template_name for c in choices}
    valid_names = set(XAC_DINH_CHA_ME_CON_REGISTRY.names())

    if re.search(
        r"thẩm quyền|cơ quan nào giải quyết|ubnd hay tòa|tòa án hay hộ tịch",
        q,
    ):
        if "tham_quyen_xac_dinh_cha_me_con" not in names:
            choices = [
                TemplateChoice(
                    template_name="tham_quyen_xac_dinh_cha_me_con",
                    reason="Safety-net: thẩm quyền Đ101",
                )
            ] + choices

    if re.search(
        r"ai có quyền yêu cầu|người giám hộ|hội liên hiệp phụ nữ|"
        r"cơ quan quản lý nhà nước",
        q,
    ) and not re.search(r"thẩm quyền|cơ quan nào xác định", q):
        if "nguoi_co_quyen_yeu_cau_xac_dinh_cha_me_con" not in names:
            choices = [
                TemplateChoice(
                    template_name="nguoi_co_quyen_yeu_cau_xac_dinh_cha_me_con",
                    reason="Safety-net: người có quyền yêu cầu Đ102",
                )
            ] + choices

    if re.search(r"tranh chấp.*(ivf|hỗ trợ sinh sản|mang thai hộ)|chưa giao.*trẻ", q):
        if "giai_quyet_tranh_chap_ho_tro_sinh_san_mang_thai_ho" not in names:
            choices = [
                TemplateChoice(
                    template_name="giai_quyet_tranh_chap_ho_tro_sinh_san_mang_thai_ho",
                    reason="Safety-net: tranh chấp Đ99",
                )
            ] + choices

    if re.search(r"ivf|hỗ trợ sinh sản|phụ nữ độc thân|cho tinh trùng|mang thai hộ", q):
        if not any(
            n in names
            for n in (
                "xac_dinh_cha_me_bang_ho_tro_sinh_san",
                "giai_quyet_tranh_chap_ho_tro_sinh_san_mang_thai_ho",
            )
        ):
            choices = [
                TemplateChoice(
                    template_name="xac_dinh_cha_me_bang_ho_tro_sinh_san",
                    reason="Safety-net: Đ93",
                )
            ] + choices

    if re.search(r"người.*yêu cầu.*đã chết|yêu cầu thay", q):
        if "xac_dinh_khi_nguoi_yeu_cau_da_chet" not in names:
            choices = [
                TemplateChoice(
                    template_name="xac_dinh_khi_nguoi_yeu_cau_da_chet",
                    reason="Safety-net: Đ92",
                )
            ] + choices

    if re.search(r"nhận cha|nhận mẹ|nhận con", q):
        if "quyen_nhan_cha_me_con" not in names and not re.search(
            r"xác định.*tòa|khai sinh|adn", q
        ):
            choices = [
                TemplateChoice(
                    template_name="quyen_nhan_cha_me_con",
                    reason="Safety-net: nhận quan hệ Đ90-91",
                )
            ] + choices

    choices = [c for c in choices if c.template_name in valid_names]
    if not choices:
        fb = _fallback_by_keywords(query)
        choices = [
            TemplateChoice(
                template_name=fb,
                reason="Safety-net fallback theo keyword",
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
        print(f"[Classifier-xac_dinh_cha_me_con] Lỗi: {exc}. Fallback.")
        fb = _fallback_by_keywords(query)
        return [TemplateChoice(template_name=fb, reason="Fallback do lỗi LLM")]

    valid_names = set(XAC_DINH_CHA_ME_CON_REGISTRY.names())
    valid = [c for c in result.choices if c.template_name in valid_names]
    if not valid and result.choices:
        bad = [c.template_name for c in result.choices]
        print(f"[Classifier-xac_dinh_cha_me_con] Template không hợp lệ: {bad}. Fallback.")
        fb = _fallback_by_keywords(query)
        valid = [TemplateChoice(template_name=fb, reason="Fallback template không hợp lệ")]
    if not valid:
        fb = _fallback_by_keywords(query)
        valid = [TemplateChoice(template_name=fb, reason="Fallback mặc định")]
    valid = _safety_net_classify(query, valid)
    print(
        f"[Classifier-xac_dinh_cha_me_con] Chọn: "
        f"{[(c.template_name, c.reason) for c in valid]}"
    )
    return valid[:2]


_EXTRACT_SYS_PROMPT_BASE = (
    "Bạn là chuyên gia trích xuất tham số cho câu Cypher truy xuất luật pháp "
    "về xác định quan hệ cha, mẹ, con. Điền chính xác các trường schema `{schema_name}`.\n\n"
    "QUY TẮC:\n"
    "1. ĐỌC description từng field — có bảng map ngữ thông tục → enum chuẩn.\n"
    "2. Không suy luận được → chọn giá trị mặc định an toàn (khong_ro, tong_quat).\n"
    "3. KHÔNG bịa enum ngoài Literal.\n"
    "4. Ly thân nhưng hôn nhân chưa chấm dứt → co_thai_trong_thoi_ky_hon_nhan hoặc ly_than.\n"
    "5. `thoi_diem_su_kien`: mốc thời gian 'YYYY-MM-DD' hoặc null."
)

_ENUM_FIELDS = {
    "tinh_huong",
    "tinh_trang_hon_nhan",
    "trong_300_ngay",
    "cha_me_cung_thua_nhan",
    "co_phu_nhan",
    "co_chung_cu",
    "huong_xac_dinh",
    "tinh_trang_ghi_nhan",
    "loai_chung_cu",
    "chu_the_nhan",
    "doi_tuong_nhan",
    "doi_tuong_da_chet",
    "chu_the_da_thanh_nien",
    "dang_co_vo_chong",
    "nguoi_khac_khong_dong_y",
    "muc_dich",
    "nguoi_co_yeu_cau_da_chet",
    "nguoi_yeu_cau_thay",
    "doi_tuong_xac_dinh",
    "vat_lieu_hien_tang",
    "quan_he_can_xac_dinh",
    "loai_vu_viec",
    "tre_da_duoc_giao",
    "tinh_trang_ben_nho_mang_thai_ho",
    "ben_mang_thai_ho_nhan_nuoi",
    "tinh_trang_tranh_chap",
    "nguoi_duoc_yeu_cau_da_chet",
    "truong_hop_dieu_92",
    "co_quan_du_kien",
    "ket_qua_can_biet",
    "kenh_yeu_cau",
    "nhom_nguoi_yeu_cau",
    "doi_tuong_duoc_bao_ve",
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


async def xac_dinh_cha_me_con(query: str) -> dict[str, Any]:
    """3 bước: classify → extract → execute → normalize."""
    print(f"[Agent xac_dinh_cha_me_con] Đang xử lý: '{query}'...")

    choices = await _classify_templates(query)

    templates: List[CypherTemplate] = []
    extract_tasks = []
    for choice in choices:
        template = XAC_DINH_CHA_ME_CON_REGISTRY.get(choice.template_name)
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
                "topic": "xac_dinh_cha_me_con",
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
