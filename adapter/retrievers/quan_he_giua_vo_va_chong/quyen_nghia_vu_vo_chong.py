"""Retriever cho chủ đề quyền, nghĩa vụ vợ chồng — Đ17-23 Luật HNGD 2014, Đ14 Luật Cư trú.

Pipeline 3 bước:
    1. CLASSIFY  -> LLM chọn 1+ template (registry topic 'quyen_nghia_vu_vo_chong').
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
from adapter.cypher_templates.quyen_nghia_vu_vo_chong import (
    QUYEN_NGHIA_VU_VO_CHONG_REGISTRY,
)
from adapter.cypher_templates.quyen_nghia_vu_vo_chong.term_mapping import resolve_term
from adapter.graph_viz import save_lazy_viz_stub
from utils.utils import chuan_hoa_Context_cho_LLM


quyen_nghia_vu_vo_chong_description = {
    "type": "function",
    "function": {
        "name": "quyen_nghia_vu_vo_chong",
        "description": (
            "Tra cứu quyền và nghĩa vụ nhân thân giữa vợ và chồng theo Điều 17-23 Luật HNGD 2014: "
            "bình đẳng, quyền nhân thân, tình nghĩa, sống chung, nơi cư trú, danh dự, "
            "tín ngưỡng/tôn giáo, nghề nghiệp, học tập và hoạt động xã hội. Không dùng để tra cứu"
            "các vấn đề liên quan đến chế độ tài sản"
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
    descriptions = QUYEN_NGHIA_VU_VO_CHONG_REGISTRY.descriptions()
    lines = ["Các template Cypher cho chủ đề 'Quyền, nghĩa vụ vợ chồng':\n"]
    for name, desc in descriptions.items():
        lines.append(f"\n- **{name}**:\n{desc}\n")
    return (
        "Bạn là router chọn template Cypher để truy xuất ngữ cảnh pháp lý cho "
        "câu hỏi về QUYỀN VÀ NGHĨA VỤ VỢ CHỒNG (Điều 17-23 Luật HNGD 2014).\n\n"
        "QUY TẮC ƯU TIÊN (theo thứ tự):\n"
        "1. Có danh dự/nhân phẩm/uy tín/thông tin riêng tư/đăng lên mạng "
        "-> ton_trong_danh_du_nhan_pham_uy_tin.\n"
        "2. Có tín ngưỡng/tôn giáo/đi lễ/theo đạo "
        "-> ton_trong_tu_do_tin_nguong_ton_giao.\n"
        "3. Có chọn nghề/đi làm/kiếm tiền/học tập/nâng cao trình độ/hoạt động chính trị, "
        "kinh tế, văn hóa, xã hội -> ho_tro_hoc_tap_lam_viec_hoat_dong_xa_hoi, "
        "TRỪ khi câu đồng thời nêu không sống chung/ly thân/sống riêng/ở tỉnh khác "
        "và hỏi lý do sống riêng.\n"
        "4. Có chuyển khẩu/nhập khẩu/nơi cư trú/phong tục/địa giới hoặc "
        "ở chung/về ở với nhà chồng/gia đình chồng -> lua_chon_noi_cu_tru. "
        "Cụm gia đình chồng + can thiệp quyền tự do cá nhân vẫn thuộc Điều 18.\n"
        "5. Có sống chung/không sống chung/ly thân/sống riêng -> nghia_vu_song_chung; "
        "nếu có ở chung với gia đình chồng thì ưu tiên lua_chon_noi_cu_tru.\n"
        "6. Có chung thủy/thương yêu/chăm sóc/giúp đỡ/công việc gia đình/nhẫn cưới/"
        "tình nghĩa vợ chồng -> tinh_nghia_vo_chong.\n"
        "7. Có quyền nhân thân/tự do cá nhân/can thiệp quyền cá nhân "
        "-> bao_ve_quyen_nghia_vu_nhan_than.\n"
        "8. Có bình đẳng/quyền nghĩa vụ ngang nhau/tự quyết mọi việc trong gia đình "
        "-> binh_dang_quyen_nghia_vu_vo_chong.\n"
        "9. Mặc định 1 template/câu; tối đa 2 khi có hai yêu cầu pháp lý độc lập.\n"
        "10. Fallback -> binh_dang_quyen_nghia_vu_vo_chong với khong_ro.\n"
        + "".join(lines)
    )


def _safety_net_classify(query: str, choices: List[TemplateChoice]) -> List[TemplateChoice]:
    q = query.lower()
    names = {c.template_name for c in choices}
    valid_names = set(QUYEN_NGHIA_VU_VO_CHONG_REGISTRY.names())

    if re.search(r"danh dự|nhân phẩm|uy tín|thông tin riêng tư|đăng.*mạng", q):
        if "ton_trong_danh_du_nhan_pham_uy_tin" not in names:
            choices = [
                TemplateChoice(
                    template_name="ton_trong_danh_du_nhan_pham_uy_tin",
                    reason="Safety-net: danh dự/nhân phẩm",
                )
            ] + choices

    if re.search(r"tín ngưỡng|tôn giáo|đi lễ|theo đạo", q):
        if "ton_trong_tu_do_tin_nguong_ton_giao" not in names:
            choices = [
                TemplateChoice(
                    template_name="ton_trong_tu_do_tin_nguong_ton_giao",
                    reason="Safety-net: tín ngưỡng/tôn giáo",
                )
            ] + choices

    if re.search(
        r"chuyển khẩu|nhập khẩu|nơi cư trú|phong tục|địa giới|"
        r"ở chung.*(nhà chồng|gia đình chồng)|về ở.*(nhà chồng|gia đình chồng)",
        q,
    ):
        if "lua_chon_noi_cu_tru" not in names and not re.search(
            r"can thiệp quyền tự do cá nhân", q
        ):
            choices = [
                TemplateChoice(
                    template_name="lua_chon_noi_cu_tru",
                    reason="Safety-net: nơi cư trú/hộ khẩu",
                )
            ] + choices

    if re.search(r"sống chung|không sống chung|sống riêng|ly thân", q):
        if "nghia_vu_song_chung" not in names and not re.search(
            r"nhà chồng|gia đình chồng|chuyển khẩu|nơi cư trú", q
        ):
            choices = [
                TemplateChoice(
                    template_name="nghia_vu_song_chung",
                    reason="Safety-net: sống chung/ly thân",
                )
            ] + choices

    if re.search(
        r"tình nghĩa|chung thủy|thương yêu|chăm sóc|giúp đỡ|công việc.*gia đình|nhẫn cưới",
        q,
    ):
        if "tinh_nghia_vo_chong" not in names:
            choices = [
                TemplateChoice(
                    template_name="tinh_nghia_vo_chong",
                    reason="Safety-net: tình nghĩa vợ chồng",
                )
            ] + choices

    if re.search(
        r"chọn nghề|đi làm|kiếm tiền|học tập|nâng cao trình độ|"
        r"hoạt động chính trị|hoạt động kinh tế|hoạt động văn hóa|hoạt động xã hội",
        q,
    ):
        if "ho_tro_hoc_tap_lam_viec_hoat_dong_xa_hoi" not in names and not re.search(
            r"không sống chung|ly thân|sống riêng|ở tỉnh khác", q
        ):
            choices = [
                TemplateChoice(
                    template_name="ho_tro_hoc_tap_lam_viec_hoat_dong_xa_hoi",
                    reason="Safety-net: nghề nghiệp/học tập/hoạt động xã hội",
                )
            ] + choices

    if re.search(r"quyền nhân thân|tự do cá nhân|can thiệp quyền", q):
        if "bao_ve_quyen_nghia_vu_nhan_than" not in names and not re.search(
            r"danh dự|tôn giáo|đi làm|nơi cư trú", q
        ):
            choices = [
                TemplateChoice(
                    template_name="bao_ve_quyen_nghia_vu_nhan_than",
                    reason="Safety-net: quyền nhân thân",
                )
            ] + choices

    if re.search(r"bình đẳng|ngang nhau|tự quyết.*mọi việc", q):
        if "binh_dang_quyen_nghia_vu_vo_chong" not in names:
            choices = [
                TemplateChoice(
                    template_name="binh_dang_quyen_nghia_vu_vo_chong",
                    reason="Safety-net: bình đẳng vợ chồng",
                )
            ] + choices

    choices = [c for c in choices if c.template_name in valid_names]
    if not choices:
        choices = [
            TemplateChoice(
                template_name="binh_dang_quyen_nghia_vu_vo_chong",
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
        print(f"[Classifier-quyen_nghia_vu_vo_chong] Lỗi: {exc}. Fallback.")
        return [
            TemplateChoice(
                template_name="binh_dang_quyen_nghia_vu_vo_chong",
                reason="Fallback do lỗi LLM",
            )
        ]

    valid_names = set(QUYEN_NGHIA_VU_VO_CHONG_REGISTRY.names())
    valid = [c for c in result.choices if c.template_name in valid_names]
    if not valid and result.choices:
        bad = [c.template_name for c in result.choices]
        print(f"[Classifier-quyen_nghia_vu_vo_chong] Template không hợp lệ: {bad}. Fallback.")
        valid = [
            TemplateChoice(
                template_name="binh_dang_quyen_nghia_vu_vo_chong",
                reason="Fallback template không hợp lệ",
            )
        ]
    if not valid:
        valid = [
            TemplateChoice(
                template_name="binh_dang_quyen_nghia_vu_vo_chong",
                reason="Fallback mặc định",
            )
        ]
    valid = _safety_net_classify(query, valid)
    print(
        f"[Classifier-quyen_nghia_vu_vo_chong] Chọn: "
        f"{[(c.template_name, c.reason) for c in valid]}"
    )
    return valid[:2]


_EXTRACT_SYS_PROMPT_BASE = (
    "Bạn là chuyên gia trích xuất tham số cho câu Cypher truy xuất luật pháp "
    "về quyền và nghĩa vụ vợ chồng. Điền chính xác các trường schema `{schema_name}`.\n\n"
    "QUY TẮC:\n"
    "1. ĐỌC description từng field — có bảng map ngữ thông tục → enum chuẩn.\n"
    "2. Không suy luận được → chọn giá trị mặc định an toàn (khong_ro, tong_quat).\n"
    "3. KHÔNG bịa enum ngoài Literal.\n"
    "4. Đi làm ở tỉnh khác + không sống chung → nghia_vu_song_chung (ngoại lệ khoản 2 Đ19), "
    "không map sang quyền nghề nghiệp Đ23.\n"
    "5. Chuyển khẩu/ở gia đình chồng → lua_chon_noi_cu_tru, không chỉ nghia_vu_song_chung.\n"
    "6. `thoi_diem_su_kien`: mốc thời gian 'YYYY-MM-DD' hoặc null. Chỉ nêu năm → 'YYYY-12-31'."
)

_ENUM_FIELDS = {
    "khia_canh_binh_dang",
    "chu_the_quyet_dinh",
    "dang_xam_pham_nhan_than",
    "chu_the_can_thiep",
    "khia_canh_tinh_nghia",
    "pham_vi_tinh_nghia",
    "tinh_huong_song_chung",
    "khia_canh_song_chung",
    "tinh_huong_cu_tru",
    "khia_canh_cu_tru",
    "hanh_vi_danh_du",
    "doi_tuong_bi_anh_huong",
    "hanh_vi_tin_nguong",
    "linh_vuc_hoat_dong",
    "dang_hanh_vi",
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


async def quyen_nghia_vu_vo_chong(query: str) -> dict[str, Any]:
    """3 bước: classify → extract → execute → normalize."""
    print(f"[Agent quyen_nghia_vu_vo_chong] Đang xử lý: '{query}'...")

    choices = await _classify_templates(query)

    templates: List[CypherTemplate] = []
    extract_tasks = []
    for choice in choices:
        template = QUYEN_NGHIA_VU_VO_CHONG_REGISTRY.get(choice.template_name)
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
                "topic": "quyen_nghia_vu_vo_chong",
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
