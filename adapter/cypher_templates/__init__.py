"""Cypher template engine cho retriever v2/v3.

Mỗi template gồm 4 phần:
- params_schema (BaseModel): Pydantic model cho LLM extract param
- description (str): mô tả để LLM-classifier chọn template
- cypher (str): câu Cypher có placeholder $param_name
- post_process (Callable, optional): hậu xử lý kết quả Cypher (mặc định trả raw)

Template được register vào TEMPLATES_REGISTRY (per topic) để retriever truy cập theo tên.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional, Type

from pydantic import BaseModel


@dataclass(frozen=True)
class CypherTemplate:
    name: str
    description: str
    params_schema: Type[BaseModel]
    cypher: str
    trace_cypher: Optional[str] = None
    """Optional Cypher chỉ chạy phần SEED và RETURN list dict
    ``{src_label, src_id, rel, dst_label, dst_id}`` để debug
    semantic seed → LegalProvision triples.

    Cùng dùng tham số như ``cypher`` (param không dùng đến sẽ được Neo4j bỏ qua).
    """
    post_process: Optional[Callable[[list[dict[str, Any]], dict[str, Any]], list[Any]]] = None
    params_builder: Optional[Callable[[BaseModel], dict[str, Any]]] = None
    """Optional hook để mở rộng dict param trước khi pass vào driver.execute_query.

    Mặc định: ``params.model_dump()``. Override nếu template cần whitelist động
    (vd whitelist_dieu_ids dựa trên khía cạnh).
    """

    def build_params(self, params: BaseModel) -> dict[str, Any]:
        if self.params_builder is not None:
            return self.params_builder(params)
        return params.model_dump()


class TemplateRegistry:
    """Registry per chủ đề (vd `tai_san`)."""

    def __init__(self, topic: str):
        self.topic = topic
        self._templates: dict[str, CypherTemplate] = {}

    def register(self, template: CypherTemplate) -> CypherTemplate:
        if template.name in self._templates:
            raise ValueError(
                f"Template '{template.name}' đã đăng ký trong topic '{self.topic}'."
            )
        self._templates[template.name] = template
        return template

    def get(self, name: str) -> CypherTemplate:
        if name not in self._templates:
            raise KeyError(
                f"Template '{name}' không tồn tại trong topic '{self.topic}'. "
                f"Available: {list(self._templates)}"
            )
        return self._templates[name]

    def all(self) -> list[CypherTemplate]:
        return list(self._templates.values())

    def names(self) -> list[str]:
        return list(self._templates.keys())

    def descriptions(self) -> dict[str, str]:
        return {name: t.description for name, t in self._templates.items()}
