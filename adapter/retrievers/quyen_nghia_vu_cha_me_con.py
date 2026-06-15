"""Retriever cho chủ đề quyền, nghĩa vụ cha mẹ và con — Đ68-74, Đ78-80 Luật HNGD 2014.

Pipeline 3 bước:
    1. CLASSIFY  -> LLM chọn 1+ template (registry topic 'quyen_nghia_vu_cha_me_con').
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
from adapter.cypher_templates.quyen_nghia_vu_cha_me_con import (
    QUYEN_NGHIA_VU_CHA_ME_CON_REGISTRY,
)
from adapter.cypher_templates.quyen_nghia_vu_cha_me_con.term_mapping import resolve_term
from adapter.graph_viz import save_lazy_viz_stub
from utils.utils import chuan_hoa_Context_cho_LLM


quyen_nghia_vu_cha_me_con_description = {
    "type": "function",
    "function": {
        "name": "quyen_nghia_vu_cha_me_con",
        "description": (
            "Tra cứu quyền và nghĩa vụ giữa cha mẹ và con trong quan hệ gia đình bình thường "
            "(không phải sau ly hôn): chăm sóc, nuôi dưỡng, giáo dục, đại diện pháp luật, "
            "bồi thường thiệt hại do con gây ra; quyền nghĩa vụ của cha nuôi/mẹ nuôi/con nuôi, "
            "cha dượng/mẹ kế/con riêng, con dâu/con rể với cha mẹ vợ/chồng. "
            "Không dùng cho tài sản riêng của con, cấp dưỡng sau ly hôn, hay quyền nuôi con sau ly hôn."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Câu hỏi cụ thể về quyền, nghĩa vụ giữa cha mẹ và con trong gia đình, "
                        "bao gồm quan hệ cha dượng/mẹ kế, con nuôi, con dâu/con rể."
                    ),
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
    descriptions = QUYEN_NGHIA_VU_CHA_ME_CON_REGISTRY.descriptions()
    lines = ["Các template Cypher cho chủ đề 'Quyền, nghĩa vụ cha mẹ và con':\n"]
    for name, desc in descriptions.items():
        lines.append(f"\n- **{name}**:\n{desc}\n")
    return (
        "Bạn là router chọn template Cypher để truy xuất ngữ cảnh pháp lý cho "
        "câu hỏi về QUYỀN VÀ NGHĨA VỤ CHA MẸ VÀ CON (Điều 68-74, 78-80 Luật HNGD 2014).\n\n"
        "QUY TẮC ƯU TIÊN (theo thứ tự):\n"
        "1. Có bồi thường/đền thiệt hại/con làm vỡ/gây thiệt hại "
        "-> boi_thuong_thiet_hai_do_con_gay_ra.\n"
        "2. Có đại diện theo pháp luật/giao dịch/hợp đồng/bán nhà/tài sản đứng tên con/"
        "đồ dùng thiết yếu -> dai_dien_va_giao_dich_cho_con.\n"
        "3. Có cha nuôi/mẹ nuôi/con nuôi/nuôi con nuôi "
        "-> quyen_nghia_vu_cha_me_nuoi_con_nuoi (trừ câu chỉ nguyên tắc bảo vệ khoản 3 Đ68).\n"
        "4. Có cha dượng/mẹ kế/con riêng của vợ hoặc chồng/con dâu/con rể/"
        "cha mẹ chồng/cha mẹ vợ -> quyen_nghia_vu_quan_he_gia_dinh_mo_rong.\n"
        "5. Có giáo dục/học tập/chọn nghề/ép học ngành/nhờ cơ quan hoặc nhà trường hỗ trợ "
        "-> giao_duc_con.\n"
        "6. Có cha mẹ ngang nhau chăm con/con chăm nuôi cha mẹ/các con cùng nuôi bố mẹ/"
        "già yếu/ốm đau -> cham_soc_nuoi_duong_giua_cha_me_con.\n"
        "7. Có hành vi cha mẹ: trông nom, nuôi dưỡng, phân biệt đối xử, lạm dụng lao động, "
        "xúi giục/ép con làm trái pháp luật -> nghia_vu_quyen_cua_cha_me "
        "(kể cả bối cảnh ly thân nếu hỏi trách nhiệm trông nom).\n"
        "8. Có quyền/bổn phận của con: sống chung, được chăm sóc, hiếu thảo, tự chọn nghề/"
        "nơi cư trú, đóng góp, quyền tài sản -> quyen_nghia_vu_cua_con "
        "(kể cả bối cảnh ly hôn nếu căn cứ Đ70).\n"
        "9. Có không phụ thuộc tình trạng hôn nhân/chưa đăng ký kết hôn/thỏa thuận ảnh hưởng "
        "quyền con/được Nhà nước bảo vệ -> bao_ve_quyen_nghia_vu_cha_me_con.\n"
        "10. Câu chung cha mẹ có quyền và nghĩa vụ gì -> nghia_vu_quyen_cua_cha_me; "
        "câu chung con có quyền và nghĩa vụ gì -> quyen_nghia_vu_cua_con.\n"
        "11. Mặc định 1 template/câu; tối đa 2 khi có hai yêu cầu pháp lý độc lập.\n"
        "12. KHÔNG seed Điều 75-77; không chuyển sang topic sau ly hôn chỉ vì có từ ly thân/ly hôn.\n"
        + "".join(lines)
    )


def _fallback_by_subject(query: str) -> str:
    q = query.lower()
    if re.search(r"con có quyền|con có nghĩa vụ|quyền.*của con|nghĩa vụ.*của con", q):
        return "quyen_nghia_vu_cua_con"
    return "nghia_vu_quyen_cua_cha_me"


def _safety_net_classify(query: str, choices: List[TemplateChoice]) -> List[TemplateChoice]:
    q = query.lower()
    names = {c.template_name for c in choices}
    valid_names = set(QUYEN_NGHIA_VU_CHA_ME_CON_REGISTRY.names())

    if re.search(r"bồi thường|đền|gây thiệt hại|làm vỡ|làm hỏng", q):
        if "boi_thuong_thiet_hai_do_con_gay_ra" not in names:
            choices = [
                TemplateChoice(
                    template_name="boi_thuong_thiet_hai_do_con_gay_ra",
                    reason="Safety-net: bồi thường thiệt hại",
                )
            ] + choices

    if re.search(
        r"đại diện theo pháp luật|giao dịch|hợp đồng|bán nhà|bán đất|"
        r"đứng tên con|nhu cầu thiết yếu|đồ dùng thiết yếu",
        q,
    ):
        if "dai_dien_va_giao_dich_cho_con" not in names:
            choices = [
                TemplateChoice(
                    template_name="dai_dien_va_giao_dich_cho_con",
                    reason="Safety-net: đại diện/giao dịch",
                )
            ] + choices

    if re.search(r"cha nuôi|mẹ nuôi|con nuôi|nuôi con nuôi", q):
        if "quyen_nghia_vu_cha_me_nuoi_con_nuoi" not in names:
            choices = [
                TemplateChoice(
                    template_name="quyen_nghia_vu_cha_me_nuoi_con_nuoi",
                    reason="Safety-net: nuôi con nuôi",
                )
            ] + choices

    if re.search(
        r"cha dượng|mẹ kế|con riêng của vợ|con riêng của chồng|"
        r"con dâu|con rể|cha mẹ chồng|cha mẹ vợ",
        q,
    ):
        if "quyen_nghia_vu_quan_he_gia_dinh_mo_rong" not in names:
            choices = [
                TemplateChoice(
                    template_name="quyen_nghia_vu_quan_he_gia_dinh_mo_rong",
                    reason="Safety-net: gia đình mở rộng",
                )
            ] + choices

    if re.search(
        r"giáo dục|học tập|chọn nghề|ngành nghề|nhờ cơ quan|nhà trường hỗ trợ|ép.*học",
        q,
    ):
        if "giao_duc_con" not in names:
            choices = [
                TemplateChoice(
                    template_name="giao_duc_con",
                    reason="Safety-net: giáo dục con",
                )
            ] + choices

    if re.search(
        r"ngang nhau.*chăm sóc|con.*chăm sóc.*cha mẹ|các con.*nuôi dưỡng|"
        r"cha mẹ già yếu|ốm đau|bị liệt",
        q,
    ):
        if "cham_soc_nuoi_duong_giua_cha_me_con" not in names:
            choices = [
                TemplateChoice(
                    template_name="cham_soc_nuoi_duong_giua_cha_me_con",
                    reason="Safety-net: chăm sóc nuôi dưỡng Đ71",
                )
            ] + choices

    if re.search(
        r"trông nom|nuôi dưỡng|phân biệt đối xử|lạm dụng.*lao động|"
        r"xúi giục|ép.*lao động|cha mẹ có quyền.*đối với con",
        q,
    ):
        if "nghia_vu_quyen_cua_cha_me" not in names and not re.search(
            r"bồi thường|đại diện|giao dịch", q
        ):
            choices = [
                TemplateChoice(
                    template_name="nghia_vu_quyen_cua_cha_me",
                    reason="Safety-net: nghĩa vụ cha mẹ Đ69",
                )
            ] + choices

    if re.search(
        r"con có quyền|con có nghĩa vụ|ngoài giá thú|sang thăm|sống chung|"
        r"tự chọn nghề|nơi cư trú",
        q,
    ):
        if "quyen_nghia_vu_cua_con" not in names and not re.search(
            r"bồi thường|đại diện|giáo dục.*ép", q
        ):
            choices = [
                TemplateChoice(
                    template_name="quyen_nghia_vu_cua_con",
                    reason="Safety-net: quyền nghĩa vụ con Đ70",
                )
            ] + choices

    if re.search(
        r"không phụ thuộc.*hôn nhân|chưa đăng ký kết hôn|thỏa thuận.*ảnh hưởng|"
        r"nhà nước bảo vệ",
        q,
    ):
        if "bao_ve_quyen_nghia_vu_cha_me_con" not in names:
            choices = [
                TemplateChoice(
                    template_name="bao_ve_quyen_nghia_vu_cha_me_con",
                    reason="Safety-net: bảo vệ Đ68",
                )
            ] + choices

    choices = [c for c in choices if c.template_name in valid_names]
    if not choices:
        fb = _fallback_by_subject(query)
        choices = [
            TemplateChoice(
                template_name=fb,
                reason="Safety-net fallback theo chủ thể",
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
        print(f"[Classifier-quyen_nghia_vu_cha_me_con] Lỗi: {exc}. Fallback.")
        fb = _fallback_by_subject(query)
        return [TemplateChoice(template_name=fb, reason="Fallback do lỗi LLM")]

    valid_names = set(QUYEN_NGHIA_VU_CHA_ME_CON_REGISTRY.names())
    valid = [c for c in result.choices if c.template_name in valid_names]
    if not valid and result.choices:
        bad = [c.template_name for c in result.choices]
        print(f"[Classifier-quyen_nghia_vu_cha_me_con] Template không hợp lệ: {bad}. Fallback.")
        fb = _fallback_by_subject(query)
        valid = [TemplateChoice(template_name=fb, reason="Fallback template không hợp lệ")]
    if not valid:
        fb = _fallback_by_subject(query)
        valid = [TemplateChoice(template_name=fb, reason="Fallback mặc định")]
    valid = _safety_net_classify(query, valid)
    print(
        f"[Classifier-quyen_nghia_vu_cha_me_con] Chọn: "
        f"{[(c.template_name, c.reason) for c in valid]}"
    )
    return valid[:2]


_EXTRACT_SYS_PROMPT_BASE = (
    "Bạn là chuyên gia trích xuất tham số cho câu Cypher truy xuất luật pháp "
    "về quyền và nghĩa vụ cha mẹ và con. Điền chính xác các trường schema `{schema_name}`.\n\n"
    "QUY TẮC:\n"
    "1. ĐỌC description từng field — có bảng map ngữ thông tục → enum chuẩn.\n"
    "2. Không suy luận được → chọn giá trị mặc định an toàn (khong_ro, tong_quat).\n"
    "3. KHÔNG bịa enum ngoài Literal.\n"
    "4. Bối cảnh ly thân/ly hôn không tự chuyển sang topic sau ly hôn nếu câu hỏi vẫn về Đ69/Đ70.\n"
    "5. Khuyết tật/bị liệt không map thành mất năng lực hành vi dân sự.\n"
    "6. Bán nhà đứng tên con -> giao_dich_tai_san_quan_trong; mẹ mua đồ thiết yếu -> giao_dich_nhu_cau_thiet_yeu.\n"
    "7. `thoi_diem_su_kien`: mốc thời gian 'YYYY-MM-DD' hoặc null. Chỉ nêu năm → 'YYYY-12-31'."
)

_ENUM_FIELDS = {
    "khia_canh_bao_ve",
    "doi_tuong_duoc_bao_ve",
    "nhom_nghia_vu_cha_me",
    "tinh_trang_cua_con",
    "boi_canh_gia_dinh",
    "nhom_quyen_nghia_vu_cua_con",
    "do_tuoi_nang_luc_cua_con",
    "tinh_trang_hon_nhan_cua_cha_me",
    "chieu_cham_soc_nuoi_duong",
    "hoan_canh_can_cham_soc",
    "so_luong_con",
    "khia_canh_giao_duc",
    "muc_do_kho_khan",
    "loai_van_de_dai_dien",
    "loai_tai_san_giao_dich",
    "chu_the_thuc_hien",
    "tinh_trang_dai_dien_khac",
    "tinh_trang_cua_con_gay_thiet_hai",
    "khia_canh_boi_thuong",
    "khia_canh_nuoi_con_nuoi",
    "trang_thai_quan_he_nuoi_con_nuoi",
    "chu_the_quan_he_nuoi_con_nuoi",
    "loai_quan_he_gia_dinh_mo_rong",
    "chieu_quyen_nghia_vu",
    "tinh_trang_song_chung",
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


async def quyen_nghia_vu_cha_me_con(query: str) -> dict[str, Any]:
    """3 bước: classify → extract → execute → normalize."""
    print(f"[Agent quyen_nghia_vu_cha_me_con] Đang xử lý: '{query}'...")

    choices = await _classify_templates(query)

    templates: List[CypherTemplate] = []
    extract_tasks = []
    for choice in choices:
        template = QUYEN_NGHIA_VU_CHA_ME_CON_REGISTRY.get(choice.template_name)
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
                "topic": "quyen_nghia_vu_cha_me_con",
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
