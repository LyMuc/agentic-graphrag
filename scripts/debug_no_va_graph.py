from adapter.config import driver
from adapter.retrievers.quan_he_giua_vo_va_chong.graph_param_resolver import build_params_for_intent
from adapter.retrievers.quan_he_giua_vo_va_chong.intent_cypher_templates import (
    INTENT_NO_VA_TRACH_NHIEM,
    build_graph_params,
    format_graph_context_for_llm,
    run_graph_retrieval,
)

QUERY = (
    "Tài sản chung của vợ chồng trong thời kì hôn nhân "
    "có được lấy để trả nợ riêng không?"
)


def main() -> None:
    params, meta = build_params_for_intent(QUERY, INTENT_NO_VA_TRACH_NHIEM)
    gp = build_graph_params(INTENT_NO_VA_TRACH_NHIEM, params)
    print("=== Params ===")
    print(gp)
    print("meta:", meta)

    graph = run_graph_retrieval(driver, INTENT_NO_VA_TRACH_NHIEM, params)
    print(f"\n=== Graph triples: {len(graph.get('graph_triples') or [])} ===")
    print(format_graph_context_for_llm(graph))


if __name__ == "__main__":
    main()
