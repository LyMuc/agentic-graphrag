"""Common Cypher snippets cho topic chia_tai_san_sau_ly_hon."""
from adapter.cypher_templates.tai_san._common import (
    EXPAND_AND_TIMEFILTER_CYPHER,
    assemble_cypher,
    assemble_simple_trace,
)

TOPIC = "chia_tai_san_sau_ly_hon"
TOPIC_LABEL = "ChiaTaiSanSauLyHon"

__all__ = [
    "EXPAND_AND_TIMEFILTER_CYPHER",
    "assemble_cypher",
    "assemble_simple_trace",
    "TOPIC",
    "TOPIC_LABEL",
]
