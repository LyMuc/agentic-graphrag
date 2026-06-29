"""Retriever cho chủ đề hạn chế quyền cha mẹ đối với con chưa thành niên (Đ85–87).

Pipeline 3 bước:
    1. CLASSIFY  -> LLM chọn 1+ template (registry topic 'han_che_quyen_cha_me_con_chua_thanh_nien').
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
from server.infrastructure.neo4j.cypher_templates.han_che_quyen_cha_me_con_chua_thanh_nien import (
    HAN_CHE_QUYEN_CHA_ME_CON_CHUA_THANH_NIEN_REGISTRY,
)
from server.infrastructure.neo4j.cypher_templates.han_che_quyen_cha_me_con_chua_thanh_nien.term_mapping import (
    resolve_term,
)
from server.infrastructure.viz.graph_viz import save_lazy_viz_stub
from server.domain.legal.codec import encode_context_record


han_che_quyen_cha_me_con_chua_thanh_nien_description = {
    "type": "function",
    "function": {
        "name": "han_che_quyen_cha_me_con_chua_thanh_nien",
        "description": (
            "Chuyên tra cứu việc Tòa án HẠN CHẾ quyền của cha, mẹ đối với con CHƯA THÀNH NIÊN "
            "khi cha mẹ vi phạm nghiêm trọng (ngược đãi, phá tan tài sản con, xúi giục...), "
            "ai có quyền khởi kiện yêu cầu hạn chế, và hậu quả pháp lý sau khi bị hạn chế. "
            "Chỉ dùng khi câu hỏi TRỰC TIẾP hỏi hạn chế/tước quyền cha mẹ với con chưa thành niên. "
            "TUYỆT ĐỐI KHÔNG dùng khi câu hỏi có bối cảnh ly hôn/sau ly hôn và hỏi gặp con, thăm nom, "
            "cấm gặp con, không cho cha/mẹ gặp con → dùng cha_me_con_sau_ly_hon. "
            "KHÔNG dùng cho quyền và nghĩa vụ cha mẹ–con bình thường (dùng quyen_nghia_vu_cha_me_con), "
            "quyền nuôi con sau ly hôn, con không nhận cha/mẹ (dùng xac_dinh_cha_me_con), "
            "hay tài sản riêng của con."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Câu hỏi về hạn chế quyền cha mẹ đối với con chưa thành niên: "
                        "hành vi bị hạn chế, thủ tục yêu cầu Tòa án, hoặc hậu quả sau khi bị hạn chế."
                    ),
                }
            },
            "required": ["query"],
        },
    },
}


class TemplateChoice(BaseModel):
    template_name: str = Field(
        description="Tên template — phải khớp 1 trong 4 template đã liệt kê."
    )
    reason: str = Field(description="Lý do ngắn (1 câu) chọn template này.")


class TemplateChoiceList(BaseModel):
    choices: List[TemplateChoice] = Field(
        description="Danh sách template phù hợp. Tối đa 2. Hầu hết câu chỉ cần 1."
    )


def _build_classifier_prompt() -> str:
    descriptions = HAN_CHE_QUYEN_CHA_ME_CON_CHUA_THANH_NIEN_REGISTRY.descriptions()
    lines = ["Các template Cypher cho chủ đề 'Hạn chế quyền cha mẹ con chưa thành niên':\n"]
    for name, desc in descriptions.items():
        lines.append(f"\n- **{name}**:\n{desc}\n")
    return (
        "Bạn là router chọn template Cypher để truy xuất ngữ cảnh pháp lý cho "
        "câu hỏi về HẠN CHẾ QUYỀN CHA MẸ ĐỐI VỚI CON CHƯA THÀNH NIÊN (Điều 85–87 LHNGD 2014).\n\n"
        "QUY TẮC ƯU TIÊN (theo thứ tự):\n"
        "1. 'Trường hợp nào/khi nào bị hạn chế', 'có bị hạn chế không', 'đi tù', "
        "'phá tài sản con', 'lối sống đồi trụy', 'ép con làm việc phạm pháp', "
        "'bị hạn chế quyền thăm nom' (nói rõ hạn chế quyền cha mẹ) "
        "-> truong_hop_pham_vi_thoi_han_han_che_quyen.\n"
        "2. 'Bị hạn chế những quyền gì', 'bao lâu/mấy năm', 'rút ngắn thời hạn' "
        "-> truong_hop_pham_vi_thoi_han_han_che_quyen.\n"
        "3. 'Ai có quyền yêu cầu/nộp đơn', 'ông bà/người giám hộ/Hội phụ nữ', "
        "'người phát hiện phải báo ai' "
        "-> nguoi_co_quyen_yeu_cau_han_che_quyen.\n"
        "4. 'Sau khi bị hạn chế ai chăm con/đại diện', 'cả cha mẹ bị hạn chế giao ai', "
        "'còn phải cấp dưỡng không' "
        "-> hau_qua_phap_ly_sau_khi_bi_han_che_quyen.\n"
        "5. Câu rộng 'trường hợp nào mẹ/cha không được nuôi con' không nói rõ cơ chế "
        "-> khong_duoc_truc_tiep_nuoi_con_va_han_che_quyen.\n"
        "6. Mặc định 1 template/câu; tối đa 2 khi có hai yêu cầu độc lập.\n"
        "7. KHÔNG bịa template name ngoài danh sách.\n"
        "8. KHÔNG chọn topic này nếu câu chỉ hỏi thăm nom/gặp con SAU LY HÔN "
        "mà không nhắc hạn chế quyền theo Điều 85.\n"
        + "".join(lines)
    )


def _safety_net_classify(query: str, choices: List[TemplateChoice]) -> List[TemplateChoice]:
    q = query.lower()
    names = {c.template_name for c in choices}

    if re.search(
        r"sau ly hôn.*(thăm|gặp) con|"
        r"(thăm|gặp) con.*sau ly hôn|"
        r"cản trở.*thăm nom|"
        r"lạm dụng.*thăm nom",
        q,
    ) and not re.search(r"hạn chế quyền|bị hạn chế|tước quyền|điều 85", q):
        return choices

    if re.search(
        r"không được nuôi|mẹ không.*nuôi|mất quyền nuôi",
        q,
    ) and not re.search(r"hạn chế|tước quyền|sau ly hôn|giành quyền", q):
        if "khong_duoc_truc_tiep_nuoi_con_va_han_che_quyen" not in names:
            choices = [
                TemplateChoice(
                    template_name="khong_duoc_truc_tiep_nuoi_con_va_han_che_quyen",
                    reason="Safety-net: câu rộng không được nuôi con",
                )
            ] + choices

    if re.search(r"đi tù|ở tù|chấp hành án", q) and re.search(
        r"có bị hạn chế|bị hạn chế không", q
    ):
        if not any(
            c.template_name == "truong_hop_pham_vi_thoi_han_han_che_quyen" for c in choices
        ):
            choices = [
                TemplateChoice(
                    template_name="truong_hop_pham_vi_thoi_han_han_che_quyen",
                    reason="Safety-net: đi tù — đối chiếu điểm a Điều 85",
                )
            ] + choices

    if re.search(
        r"ai (được| có quyền).*yêu cầu|nộp đơn|đề nghị cơ quan",
        q,
    ):
        if not any(
            c.template_name == "nguoi_co_quyen_yeu_cau_han_che_quyen" for c in choices
        ):
            choices = [
                TemplateChoice(
                    template_name="nguoi_co_quyen_yeu_cau_han_che_quyen",
                    reason="Safety-net: ai yêu cầu Tòa án",
                )
            ] + choices

    if re.search(
        r"sau khi bị hạn chế|ai chăm con|giao cho.*giám hộ|còn.*cấp dưỡng",
        q,
    ):
        if not any(
            c.template_name == "hau_qua_phap_ly_sau_khi_bi_han_che_quyen" for c in choices
        ):
            choices = [
                TemplateChoice(
                    template_name="hau_qua_phap_ly_sau_khi_bi_han_che_quyen",
                    reason="Safety-net: hậu quả Điều 87",
                )
            ] + choices

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
        print(f"[Classifier-han_che_quyen] Lỗi: {exc}. Fallback trường hợp hạn chế.")
        return [
            TemplateChoice(
                template_name="truong_hop_pham_vi_thoi_han_han_che_quyen",
                reason="Fallback do lỗi LLM",
            )
        ]

    valid_names = set(HAN_CHE_QUYEN_CHA_ME_CON_CHUA_THANH_NIEN_REGISTRY.names())
    valid = [c for c in result.choices if c.template_name in valid_names]
    if not valid and result.choices:
        bad = [c.template_name for c in result.choices]
        print(f"[Classifier-han_che_quyen] Template không hợp lệ: {bad}. Fallback.")
        valid = [
            TemplateChoice(
                template_name="truong_hop_pham_vi_thoi_han_han_che_quyen",
                reason="Fallback template không hợp lệ",
            )
        ]
    if not valid:
        valid = [
            TemplateChoice(
                template_name="truong_hop_pham_vi_thoi_han_han_che_quyen",
                reason="Fallback mặc định",
            )
        ]
    valid = _safety_net_classify(query, valid)
    print(
        f"[Classifier-han_che_quyen] Chọn: "
        f"{[(c.template_name, c.reason) for c in valid]}"
    )
    return valid[:2]


_EXTRACT_SYS_PROMPT_BASE = (
    "Bạn là chuyên gia trích xuất tham số cho câu Cypher truy xuất luật pháp "
    "về hạn chế quyền cha mẹ đối với con chưa thành niên. "
    "Điền chính xác các trường schema `{schema_name}`.\n\n"
    "QUY TẮC:\n"
    "1. ĐỌC description từng field — có bảng map ngữ thông tục → enum chuẩn.\n"
    "2. Không suy luận được → chọn giá trị mặc định an toàn (khong_ro, tong_quat, tat_ca).\n"
    "3. KHÔNG bịa enum ngoài Literal.\n"
    "4. 'Đi tù/ở tù' → bi_ket_an_khong_ro_toi_danh; KHÔNG tự kết luận đủ căn cứ hạn chế.\n"
    "5. 'Thăm nom' trong câu nói rõ hạn chế quyền cha mẹ → tham_nom_cach_noi_doi_thuong.\n"
    "6. 'Mẹ không được nuôi con' câu rộng → boi_canh_nuoi_con=giao_thoa.\n"
    "7. `thoi_diem_su_kien`: mốc thời gian 'YYYY-MM-DD' hoặc null. Chỉ nêu năm → 'YYYY-12-31'."
)

_ENUM_FIELDS = {
    "doi_tuong_bi_han_che",
    "khia_canh_han_che",
    "nhom_can_cu_hanh_vi",
    "quyen_bi_hoi",
    "nhom_chu_the_yeu_cau",
    "khia_canh_yeu_cau",
    "tinh_trang_cha_me",
    "khia_canh_hau_qua",
    "quyen_nghia_vu_duoc_hoi",
    "doi_tuong_phu_huynh",
    "boi_canh_nuoi_con",
    "do_tuoi_con",
    "khia_canh_nuoi_con",
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


async def han_che_quyen_cha_me_con_chua_thanh_nien(query: str) -> dict[str, Any]:
    """3 bước: classify → extract → execute → normalize."""
    print(f"[Agent han_che_quyen_cha_me_con_chua_thanh_nien] Đang xử lý: '{query}'...")

    choices = await _classify_templates(query)

    templates: List[CypherTemplate] = []
    extract_tasks = []
    for choice in choices:
        template = HAN_CHE_QUYEN_CHA_ME_CON_CHUA_THANH_NIEN_REGISTRY.get(choice.template_name)
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
                    retriever_name="han_che_quyen_cha_me_con_chua_thanh_nien",
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
                "topic": "han_che_quyen_cha_me_con_chua_thanh_nien",
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


class HanCheQuyenChaMeConChuaThanhNienRetriever(RetrieverAgent):
    """Subagent ``han_che_quyen_cha_me_con_chua_thanh_nien`` — thin wrapper ủy quyền pipeline classify→extract→execute→run."""

    name = "han_che_quyen_cha_me_con_chua_thanh_nien"
    description = han_che_quyen_cha_me_con_chua_thanh_nien_description

    async def classify(self, query: str):
        return await _classify_templates(query)

    async def extract(self, query: str, template):
        return await _extract_template_params(query, template)

    async def execute(self, template, params, target_date: str):
        return _run_template_sync(template, params, target_date)

    async def run(self, query: str):
        return await han_che_quyen_cha_me_con_chua_thanh_nien(query)
