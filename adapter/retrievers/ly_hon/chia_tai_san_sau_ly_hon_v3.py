"""Retriever V3 cho chủ đề "Chia tài sản sau ly hôn" — Điều 59-64 Luật HNGD 2014.

Pipeline 3 bước:
    1. CLASSIFY  -> LLM chọn 1+ template (registry topic 'chia_tai_san_sau_ly_hon').
    2. EXTRACT   -> LLM extract param (Pydantic) + thời điểm sự kiện.
    3. EXECUTE   -> chạy Cypher qua asyncio.to_thread → chuan_hoa_Context_cho_LLM.

Output: dict ``{"contexts": list[str], "debug": str}``.
"""
from __future__ import annotations

import asyncio
import json
from datetime import date
from typing import Any, List

from pydantic import BaseModel, Field

from adapter.config import driver, build_llm, RETRIEVER_LLM
from adapter.cypher_templates import CypherTemplate
from adapter.cypher_templates.chia_tai_san_sau_ly_hon import (
    CHIA_TAI_SAN_SAU_LY_HON_REGISTRY,
)
from adapter.cypher_templates.chia_tai_san_sau_ly_hon.term_mapping import resolve_term
from utils.utils import chuan_hoa_Context_cho_LLM


chia_tai_san_sau_ly_hon_v3_description = {
    "type": "function",
    "function": {
        "name": "chia_tai_san_sau_ly_hon_v3",
        "description": (
            "Tra cứu các quy định về CHIA TÀI SẢN SAU LY HÔN (Điều 59-64 "
            "Luật Hôn nhân & Gia đình 2014). Bao gồm: nguyên tắc chia tài sản, "
            "tài sản cụ thể, nghĩa vụ với người thứ ba, quyền sử dụng đất, "
            "sống chung gia đình/lưu cư, tài sản chung đưa vào kinh doanh. "
            "Dùng KG ngữ nghĩa mới (6 template Cypher).\n\n"
            "KHÔNG dùng cho câu hỏi 'chế độ tài sản trong hôn nhân' (Đ28-50) "
            "hay 'chia tài sản TRONG thời kỳ hôn nhân' (Đ38-42)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Câu hỏi cụ thể của người dùng (giữ nguyên).",
                }
            },
            "required": ["query"],
        },
    },
}


class TemplateChoice(BaseModel):
    template_name: str = Field(
        description="Tên template — phải khớp 1 trong 6 template đã liệt kê."
    )
    reason: str = Field(description="Lý do ngắn (1 câu) chọn template này.")


class TemplateChoiceList(BaseModel):
    choices: List[TemplateChoice] = Field(
        description="Danh sách template phù hợp. Tối đa 2. Hầu hết câu chỉ cần 1."
    )


def _build_classifier_prompt() -> str:
    descriptions = CHIA_TAI_SAN_SAU_LY_HON_REGISTRY.descriptions()
    lines = [
        "Các template Cypher cho chủ đề 'Chia tài sản sau ly hôn':\n"
    ]
    for name, desc in descriptions.items():
        lines.append(f"\n- **{name}**:\n{desc}\n")
    return (
        "Bạn là router chọn template Cypher để truy xuất ngữ cảnh pháp lý cho "
        "câu hỏi về CHIA TÀI SẢN KHI/Sau LY HÔN.\n\n"
        "QUY TẮC ƯU TIÊN (theo thứ tự):\n"
        "1. 'quyền sử dụng đất', 'đất', 'sổ đỏ', 'mua đất' + chia khi ly hôn "
        "→ chia_quyen_su_dung_dat_khi_ly_hon.\n"
        "2. 'lưu cư', 'ở lại nhà riêng', 'khó khăn chỗ ở', 'nhà riêng vợ/chồng' "
        "→ truong_hop_nha_o_gia_dinh_va_luu_cu.\n"
        "3. 'sống chung với gia đình', 'khối tài sản chung gia đình' (không phải "
        "QSDĐ thuần) → truong_hop_nha_o_gia_dinh_va_luu_cu.\n"
        "4. 'nợ', 'vay', 'trả nợ', 'ngân hàng', 'chủ nợ', 'người thứ ba', "
        "'nghĩa vụ tài sản' → nghia_vu_tai_san_voi_nguoi_thu_ba_khi_ly_hon.\n"
        "5. 'đưa vào kinh doanh', 'tài sản kinh doanh', 'góp vốn', 'làm ăn' "
        "+ chia tài sản → tai_san_chung_dua_vao_kinh_doanh_khi_ly_hon.\n"
        "6. 'nguyên tắc', 'chia đôi', 'chia đều', '50/50', 'yếu tố', 'công sức', "
        "'nội trợ', 'chăm con', 'lỗi', 'gian dối', 'ngoại tình' "
        "→ nguyen_tac_chia_tai_san_ly_hon.\n"
        "7. Tài sản cụ thể (nhà trả góp, đứng tên, trợ cấp, quà cưới, ô tô, "
        "tiền được cho riêng) → tai_san_cu_the_khi_ly_hon.\n"
        "8. Fallback → nguyen_tac_chia_tai_san_ly_hon (khia_canh=tong_quat).\n\n"
        "KHÔNG chọn template ngoài danh sách. Mặc định 1 template/câu.\n"
        "KHÔNG dùng cho câu hỏi chế độ tài sản trong hôn nhân (Đ28-50) "
        "hoặc chia tài sản TRONG hôn nhân (Đ38-42).\n"
        + "".join(lines)
    )


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
        print(f"[Classifier-v3-ly_hon] Lỗi: {exc}. Fallback nguyen_tac.")
        return [
            TemplateChoice(
                template_name="nguyen_tac_chia_tai_san_ly_hon",
                reason="Fallback do lỗi LLM",
            )
        ]

    valid_names = set(CHIA_TAI_SAN_SAU_LY_HON_REGISTRY.names())
    valid = [c for c in result.choices if c.template_name in valid_names]
    if not valid and result.choices:
        bad = [c.template_name for c in result.choices]
        print(f"[Classifier-v3-ly_hon] Template không hợp lệ: {bad}. Fallback.")
        valid = [
            TemplateChoice(
                template_name="nguyen_tac_chia_tai_san_ly_hon",
                reason="Fallback template không hợp lệ",
            )
        ]
    if not valid:
        valid = [
            TemplateChoice(
                template_name="nguyen_tac_chia_tai_san_ly_hon",
                reason="Fallback mặc định",
            )
        ]
    print(f"[Classifier-v3-ly_hon] Chọn: {[(c.template_name, c.reason) for c in valid]}")
    return valid[:2]


class _ThoiDiem(BaseModel):
    thoi_diem_su_kien: str | None = Field(
        default=None,
        description="Mốc thời gian 'YYYY-MM-DD' hoặc null.",
    )


_EXTRACT_SYS_PROMPT_BASE = (
    "Bạn là chuyên gia trích xuất tham số cho câu Cypher truy xuất luật pháp "
    "về chia tài sản sau ly hôn. Điền chính xác các trường schema `{schema_name}`.\n\n"
    "QUY TẮC:\n"
    "1. ĐỌC description từng field — có bảng map ngữ thông tục → enum chuẩn.\n"
    "2. Không suy luận được → chọn giá trị mặc định an toàn (khong_ro, tat_ca, chua_ro).\n"
    "3. KHÔNG bịa enum ngoài Literal."
)

_ENUM_FIELDS = {
    "khia_canh",
    "loai_tai_san",
    "nguon_goc",
    "tinh_chat_du_kien",
    "da_chia_va_thanh_toan",
    "loai_nghia_vu",
    "nguoi_thu_ba",
    "thoi_diem_no",
    "muc_dich_no",
    "tinh_chat_qsd_dat",
    "loai_dat",
    "ho_gia_dinh",
    "nhu_cau_su_dung",
    "hanh_vi_context",
    "loai_truong_hop",
    "xac_dinh_duoc_phan_tai_san",
    "kho_khan_cho_o",
    "thoa_thuan_khac",
    "nguoi_dang_kinh_doanh",
    "tai_san_chung_lien_quan_kinh_doanh",
    "phap_luat_kinh_doanh_khac",
}


def _normalize_with_term_mapping(params: BaseModel, query: str) -> BaseModel:
    data = params.model_dump()
    changed = False
    q_norm = query.lower()

    for field_name in _ENUM_FIELDS:
        if field_name not in data:
            continue
        current = data.get(field_name)
        if current and current not in ("khong_ro", "chua_ro", "tat_ca"):
            continue
        resolved = resolve_term(field_name, query)
        if resolved and resolved != current:
            print(f"[term_mapping] {field_name}: '{current}' → '{resolved}'")
            data[field_name] = resolved
            changed = True

    # Cross-field hints từ query
    if "loai_nghia_vu" in data and "vay" in q_norm and "kinh doanh" in q_norm:
        if data.get("loai_nghia_vu") == "khong_ro":
            data["loai_nghia_vu"] = "vay_kinh_doanh"
            data["muc_dich_no"] = "kinh_doanh"
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
    schema_name = template.params_schema.__name__
    sys_prompt = _EXTRACT_SYS_PROMPT_BASE.format(schema_name=schema_name)
    llm = build_llm(model=RETRIEVER_LLM, temperature=0)

    params_struct_llm = llm.with_structured_output(template.params_schema)
    date_struct_llm = llm.with_structured_output(_ThoiDiem)

    params_task = params_struct_llm.ainvoke(
        [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": f"Câu hỏi: {query}"},
        ]
    )
    date_task = date_struct_llm.ainvoke(
        [
            {
                "role": "system",
                "content": (
                    "Xác định mốc thời gian sự kiện (YYYY-MM-DD) hoặc null."
                ),
            },
            {"role": "user", "content": f"Câu hỏi: {query}"},
        ]
    )

    params, date_obj = await asyncio.gather(params_task, date_task)
    params = _normalize_with_term_mapping(params, query)
    return params, date_obj.thoi_diem_su_kien


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
    return {
        k: v
        for k, v in runtime_params.items()
        if "whitelist" not in k.lower() and "allowed_semantic" not in k.lower()
    }


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


async def chia_tai_san_sau_ly_hon_v3(query: str) -> dict[str, Any]:
    """3 bước: classify → extract → execute → normalize."""
    print(f"[Agent chia_tai_san_sau_ly_hon_v3] Đang xử lý: '{query}'...")

    choices = await _classify_templates(query)

    templates: List[CypherTemplate] = []
    extract_tasks = []
    for choice in choices:
        template = CHIA_TAI_SAN_SAU_LY_HON_REGISTRY.get(choice.template_name)
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

    return {"contexts": contexts, "debug": "\n\n".join(debug_parts)}
