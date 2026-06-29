"""Schema helpers: single LLM call for template params + thoi_diem_su_kien."""
from __future__ import annotations

from functools import lru_cache
from typing import Type

from pydantic import BaseModel, Field, create_model

THOI_DIEM_DESC = (
    "Mốc thời gian sự kiện trong câu hỏi, định dạng 'YYYY-MM-DD'. "
    "Trả null nếu câu hỏi KHÔNG nêu mốc thời gian cụ thể."
)


@lru_cache(maxsize=64)
def build_params_with_date_schema(params_schema: Type[BaseModel]) -> Type[BaseModel]:
    """Extend a template params schema with thoi_diem_su_kien for one-shot extract."""
    return create_model(
        f"{params_schema.__name__}WithThoiDiem",
        __base__=params_schema,
        thoi_diem_su_kien=(
            str | None,
            Field(default=None, description=THOI_DIEM_DESC),
        ),
    )


def split_params_and_date(
    extracted: BaseModel, params_schema: Type[BaseModel]
) -> tuple[BaseModel, str | None]:
    """Split combined extract output into params instance and optional date."""
    data = extracted.model_dump()
    date_val = data.pop("thoi_diem_su_kien", None)
    return params_schema(**data), date_val
