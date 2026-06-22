"""Lightweight tool descriptions for the Router LLM (no Chainlit, no retriever execution).

Built from RETRIEVER_SPECS plus direct tools (clarify, respond, text2cypher).
Used by benchmark scripts that only need router output, not full chatbot runtime.
"""

from __future__ import annotations

from typing import Any

from application.retriever_catalog import RetrieverSpec, unique_retriever_specs

# Inlined from utils/general.py to avoid importing Neo4j driver.
RESPOND_DESCRIPTION: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "respond",
        "description": (
            "Nếu cuộc hội thoại đã chứa một câu trả lời hoàn chỉnh cho câu hỏi, "
            "hãy sử dụng công cụ này để trích xuất nó. Ngoài ra, nếu người dùng "
            "trò chuyện phiếm, hãy dùng công cụ này để nhắc họ rằng bạn chỉ có thể "
            "trả lời các câu hỏi liên quan đến luật hôn nhân gia đình."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "answer": {
                    "type": "string",
                    "description": "Phản hồi trực tiếp bằng câu trả lời",
                }
            },
            "required": ["answer"],
        },
    },
}

TEXT2CYPHER_DESCRIPTION: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "text2cypher",
        "description": (
            "Truy vấn cơ sở dữ liệu đồ thị bằng câu hỏi của người dùng. "
            "Khi các công cụ khác không phù hợp, hãy sử dụng công cụ này "
            "làm phương án dự phòng (fallback)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Câu hỏi của người dùng cần tìm câu trả lời",
                }
            },
            "required": ["query"],
        },
    },
}

CLARIFY_DESCRIPTION: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "clarify",
        "description": (
            "Hỏi lại người dùng khi câu follow-up có từ hai cách hiểu hợp lý trở lên "
            "và lịch sử gần cùng chỉ mục lượt cũ không đủ để xác định chắc chắn. "
            "Không dùng nếu câu hỏi tự nó đã đầy đủ hoặc có thể trả lời theo các trường hợp."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "Câu hỏi ngắn để làm rõ ý người dùng.",
                }
            },
            "required": ["question"],
        },
    },
}

DIRECT_TOOL_DESCRIPTIONS: dict[str, dict[str, Any]] = {
    "clarify": CLARIFY_DESCRIPTION,
    "respond": RESPOND_DESCRIPTION,
    "text2cypher": TEXT2CYPHER_DESCRIPTION,
}


def _spec_description_text(spec: RetrieverSpec) -> str:
    reasons: list[str] = []
    for trigger in spec.required_triggers + spec.support_triggers:
        if trigger.reason and trigger.reason not in reasons:
            reasons.append(trigger.reason)
    if reasons:
        return " ".join(reasons[:3])
    return f"Tra cứu quy định pháp lý về chủ đề {spec.topic_label}."


def spec_to_tool_description(spec: RetrieverSpec) -> dict[str, Any]:
    if spec.router_description_schema is not None:
        return spec.router_description_schema
    return {
        "type": "function",
        "function": {
            "name": spec.name,
            "description": _spec_description_text(spec),
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


def router_tool_registry() -> dict[str, dict[str, Any]]:
    """Return {tool_name: {description: openai_function_schema}} for all router tools."""
    registry: dict[str, dict[str, Any]] = {}
    for spec in unique_retriever_specs():
        registry[spec.name] = {"description": spec_to_tool_description(spec)}
    for tool_name, description in DIRECT_TOOL_DESCRIPTIONS.items():
        registry[tool_name] = {"description": description}
    return registry


def router_tools_for_llm() -> list[dict[str, Any]]:
    """OpenAI/LangChain tool schemas to pass into tool_choice / bind_tools."""
    return [entry["description"] for entry in router_tool_registry().values()]
