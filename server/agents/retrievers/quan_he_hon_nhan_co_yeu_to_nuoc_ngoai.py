"""Retriever cho chủ đề quan hệ HNGĐ có yếu tố nước ngoài — Đ121-130 Luật HNGD 2014.

Pipeline 3 bước:
    1. CLASSIFY  -> LLM chọn 1+ template (registry topic 'quan_he_hon_nhan_co_yeu_to_nuoc_ngoai').
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

from server.infrastructure.neo4j.client import driver
from server.infrastructure.llm.factory import build_llm, RETRIEVER_LLM
from server.infrastructure.neo4j.cypher_templates import CypherTemplate
from server.infrastructure.neo4j.cypher_templates.extract_schema import (
    build_params_with_date_schema,
    split_params_and_date,
)
from server.infrastructure.neo4j.cypher_templates.quan_he_hon_nhan_co_yeu_to_nuoc_ngoai import (
    QUAN_HE_HON_NHAN_CO_YEU_TO_NUOC_NGOAI_REGISTRY,
)
from server.infrastructure.neo4j.cypher_templates.quan_he_hon_nhan_co_yeu_to_nuoc_ngoai.term_mapping import (
    resolve_term,
)
from server.infrastructure.viz.graph_viz import save_lazy_viz_stub
from server.domain.legal.codec import encode_context_record


quan_he_hon_nhan_co_yeu_to_nuoc_ngoai_description = {
    "type": "function",
    "function": {
        "name": "quan_he_hon_nhan_co_yeu_to_nuoc_ngoai",
        "description": (
            "Tra cứu quy định về quan hệ hôn nhân và gia đình có yếu tố nước ngoài "
            "(Điều 121-130): bảo vệ quyền lợi, áp dụng pháp luật, thẩm quyền, hợp pháp hóa "
            "giấy tờ, công nhận bản án nước ngoài, kết hôn/ly hôn, xác định cha mẹ con, "
            "cấp dưỡng và tài sản/chung sống không đăng ký."
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
    descriptions = QUAN_HE_HON_NHAN_CO_YEU_TO_NUOC_NGOAI_REGISTRY.descriptions()
    lines = [
        "Các template Cypher cho chủ đề 'Quan hệ HNGĐ có yếu tố nước ngoài':\n"
    ]
    for name, desc in descriptions.items():
        lines.append(f"\n- **{name}**:\n{desc}\n")
    return (
        "Bạn là router chọn template Cypher để truy xuất ngữ cảnh pháp lý cho "
        "câu hỏi về QUAN HỆ HÔN NHÂN VÀ GIA ĐÌNH CÓ YẾU TỐ NƯỚC NGOÀI (Đ121-130).\n\n"
        "QUY TẮC ƯU TIÊN (theo thứ tự):\n"
        "1. Có hợp pháp hóa lãnh sự/giấy tờ/tài liệu nước ngoài "
        "→ hop_phap_hoa_lanh_su_giay_to.\n"
        "2. Có bản án/quyết định Tòa án hoặc cơ quan nước ngoài, ghi sổ hộ tịch, "
        "yêu cầu thi hành → cong_nhan_ghi_chu_ban_an_nuoc_ngoai.\n"
        "3. Có xác định/nhận cha, mẹ, con → xac_dinh_cha_me_con_co_yeu_to_nuoc_ngoai "
        "(kể cả hỏi cơ quan nào).\n"
        "4. Có cấp dưỡng → cap_duong_co_yeu_to_nuoc_ngoai.\n"
        "5. Có ly hôn/thuận tình/đơn phương → ly_hon_co_yeu_to_nuoc_ngoai "
        "(tài sản BĐS nước ngoài trong cùng câu vẫn do template này).\n"
        "6. Có kết hôn VN-người nước ngoài hoặc hai người nước ngoài thường trú VN "
        "→ ket_hon_co_yeu_to_nuoc_ngoai.\n"
        "7. Có chế độ tài sản theo thỏa thuận hoặc chung sống không đăng ký "
        "→ tai_san_thoa_thuan_va_chung_song_khong_dang_ky.\n"
        "8. Có đăng ký hộ tịch/Tòa án/cấp huyện/biên giới nhưng không trúng 2-5 "
        "→ tham_quyen_vu_viec_yeu_to_nuoc_ngoai.\n"
        "9. Có điều ước quốc tế/dẫn chiếu pháp luật nước ngoài/dẫn chiếu trở lại "
        "mà không có nghiệp vụ cụ thể ở 3-7 → ap_dung_phap_luat_yeu_to_nuoc_ngoai.\n"
        "10. Có tôn trọng/bảo vệ/bảo hộ/Chính phủ quy định chi tiết "
        "→ bao_ve_quyen_loi_yeu_to_nuoc_ngoai.\n"
        "11. 'Pháp luật nào' KHÔNG tự chọn Điều 122 nếu câu đã nêu kết hôn/ly hôn/"
        "cấp dưỡng/Điều 130.\n"
        "12. 'Thẩm quyền/cơ quan nào' KHÔNG tự chọn Điều 123 nếu câu đã nêu nghiệp vụ "
        "ở rule 2-5.\n"
        "13. Mặc định 1 template/câu; tối đa 2 khi có hai nghiệp vụ độc lập.\n"
        "14. Fallback → bao_ve_quyen_loi_yeu_to_nuoc_ngoai; không bịa template name.\n"
        + "".join(lines)
    )


def _safety_net_classify(query: str, choices: List[TemplateChoice]) -> List[TemplateChoice]:
    q = query.lower()
    names = {c.template_name for c in choices}

    if re.search(r"hợp pháp hóa|giấy tờ.*nước ngoài|tài liệu.*nước ngoài", q):
        if "hop_phap_hoa_lanh_su_giay_to" not in names:
            choices = [
                TemplateChoice(
                    template_name="hop_phap_hoa_lanh_su_giay_to",
                    reason="Safety-net: hợp pháp hóa giấy tờ",
                )
            ] + choices

    if re.search(
        r"bản án.*nước ngoài|quyết định.*nước ngoài|ghi.*sổ hộ tịch|yêu cầu thi hành",
        q,
    ):
        if "cong_nhan_ghi_chu_ban_an_nuoc_ngoai" not in names:
            choices = [
                TemplateChoice(
                    template_name="cong_nhan_ghi_chu_ban_an_nuoc_ngoai",
                    reason="Safety-net: bản án nước ngoài",
                )
            ] + choices

    if re.search(r"xác định.*cha|xác định.*mẹ|nhận cha|nhận mẹ|nhận con", q):
        if "xac_dinh_cha_me_con_co_yeu_to_nuoc_ngoai" not in names:
            choices = [
                TemplateChoice(
                    template_name="xac_dinh_cha_me_con_co_yeu_to_nuoc_ngoai",
                    reason="Safety-net: xác định cha mẹ con",
                )
            ] + choices

    if re.search(r"cấp dưỡng", q):
        if "cap_duong_co_yeu_to_nuoc_ngoai" not in names:
            choices = [
                TemplateChoice(
                    template_name="cap_duong_co_yeu_to_nuoc_ngoai",
                    reason="Safety-net: cấp dưỡng",
                )
            ] + choices

    if re.search(r"ly hôn|thuận tình|đơn phương|ly thân", q):
        if "ly_hon_co_yeu_to_nuoc_ngoai" not in names:
            choices = [
                TemplateChoice(
                    template_name="ly_hon_co_yeu_to_nuoc_ngoai",
                    reason="Safety-net: ly hôn",
                )
            ] + choices

    if re.search(r"kết hôn", q) and re.search(
        r"người nước ngoài|thường trú tại việt nam|công dân việt nam.*người", q
    ):
        if "ket_hon_co_yeu_to_nuoc_ngoai" not in names:
            choices = [
                TemplateChoice(
                    template_name="ket_hon_co_yeu_to_nuoc_ngoai",
                    reason="Safety-net: kết hôn yếu tố nước ngoài",
                )
            ] + choices

    valid_names = set(QUAN_HE_HON_NHAN_CO_YEU_TO_NUOC_NGOAI_REGISTRY.names())
    choices = [c for c in choices if c.template_name in valid_names]
    if not choices:
        choices = [
            TemplateChoice(
                template_name="bao_ve_quyen_loi_yeu_to_nuoc_ngoai",
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
        print(f"[Classifier-quan_he_hon_nhan_co_yeu_to_nuoc_ngoai] Lỗi: {exc}. Fallback.")
        return [
            TemplateChoice(
                template_name="bao_ve_quyen_loi_yeu_to_nuoc_ngoai",
                reason="Fallback do lỗi LLM",
            )
        ]

    valid_names = set(QUAN_HE_HON_NHAN_CO_YEU_TO_NUOC_NGOAI_REGISTRY.names())
    valid = [c for c in result.choices if c.template_name in valid_names]
    if not valid and result.choices:
        bad = [c.template_name for c in result.choices]
        print(
            f"[Classifier-quan_he_hon_nhan_co_yeu_to_nuoc_ngoai] Template không hợp lệ: {bad}."
        )
        valid = [
            TemplateChoice(
                template_name="bao_ve_quyen_loi_yeu_to_nuoc_ngoai",
                reason="Fallback template không hợp lệ",
            )
        ]
    if not valid:
        valid = [
            TemplateChoice(
                template_name="bao_ve_quyen_loi_yeu_to_nuoc_ngoai",
                reason="Fallback mặc định",
            )
        ]
    valid = _safety_net_classify(query, valid)
    print(
        f"[Classifier-quan_he_hon_nhan_co_yeu_to_nuoc_ngoai] Chọn: "
        f"{[(c.template_name, c.reason) for c in valid]}"
    )
    return valid[:2]


_EXTRACT_SYS_PROMPT_BASE = (
    "Bạn là chuyên gia trích xuất tham số cho câu Cypher truy xuất luật pháp "
    "về quan hệ hôn nhân và gia đình có yếu tố nước ngoài (Đ121-130). "
    "Điền chính xác các trường schema `{schema_name}`.\n\n"
    "QUY TẮC:\n"
    "1. ĐỌC description từng field — có bảng map ngữ thông tục → enum chuẩn.\n"
    "2. Không suy luận được → chọn giá trị mặc định an toàn (khong_ro, tong_quat).\n"
    "3. KHÔNG bịa enum ngoài Literal.\n"
    "4. Cấp dưỡng: KHÔNG suy nơi cư trú người yêu cầu từ nơi làm việc/quốc tịch "
    "người có nghĩa vụ — giữ khong_ro và seed cả hai rule khoản 1.\n"
    "5. `thoi_diem_su_kien`: mốc thời gian 'YYYY-MM-DD' hoặc null nếu không nêu ngày."
)

_ENUM_FIELDS = {
    "pham_vi_bao_ve",
    "khia_canh_bao_ve",
    "co_so_ap_dung",
    "khia_canh_ap_dung",
    "loai_vu_viec",
    "dia_ban",
    "chu_the_doi_ung",
    "khia_canh_tham_quyen",
    "nguon_giay_to",
    "muc_dich_su_dung",
    "can_cu_mien",
    "khia_canh_hop_phap_hoa",
    "loai_quyet_dinh",
    "nhu_cau_thi_hanh",
    "co_don_yeu_cau_khong_cong_nhan",
    "khia_canh_ban_an",
    "nhom_chu_the",
    "noi_tien_hanh_ket_hon",
    "ben_can_xet",
    "khia_canh_ket_hon",
    "hinh_thuc_ly_hon",
    "tinh_trang_noi_thuong_tru_chung",
    "loai_tai_san",
    "khia_canh_ly_hon",
    "co_tranh_chap",
    "khia_canh_xac_dinh",
    "tinh_trang_cu_tru_nguoi_yeu_cau",
    "khia_canh_cap_duong",
    "dang_quan_he",
    "yeu_cau_giai_quyet",
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


async def quan_he_hon_nhan_co_yeu_to_nuoc_ngoai(query: str) -> dict[str, Any]:
    """3 bước: classify → extract → execute → normalize."""
    print(f"[Agent quan_he_hon_nhan_co_yeu_to_nuoc_ngoai] Đang xử lý: '{query}'...")

    choices = await _classify_templates(query)

    templates: List[CypherTemplate] = []
    extract_tasks = []
    for choice in choices:
        template = QUAN_HE_HON_NHAN_CO_YEU_TO_NUOC_NGOAI_REGISTRY.get(choice.template_name)
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
                    retriever_name="quan_he_hon_nhan_co_yeu_to_nuoc_ngoai",
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
                "topic": "quan_he_hon_nhan_co_yeu_to_nuoc_ngoai",
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


from server.agents.retrievers.base import RetrieverAgent


class QuanHeHonNhanCoYeuToNuocNgoaiRetriever(RetrieverAgent):
    """Subagent ``quan_he_hon_nhan_co_yeu_to_nuoc_ngoai`` — thin wrapper ủy quyền pipeline classify→extract→execute→run."""

    name = "quan_he_hon_nhan_co_yeu_to_nuoc_ngoai"
    description = quan_he_hon_nhan_co_yeu_to_nuoc_ngoai_description

    async def classify(self, query: str):
        return await _classify_templates(query)

    async def extract(self, query: str, template):
        return await _extract_template_params(query, template)

    async def execute(self, template, params, target_date: str):
        return _run_template_sync(template, params, target_date)

    async def run(self, query: str):
        return await quan_he_hon_nhan_co_yeu_to_nuoc_ngoai(query)
