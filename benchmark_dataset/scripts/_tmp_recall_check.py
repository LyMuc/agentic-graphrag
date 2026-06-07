import json
from pathlib import Path
data = json.loads(Path("benchmark_dataset/router_eval/router_agent_test.json").read_text(encoding="utf-8"))
degraded = [x for x in data if x.get("recall") is not None and x.get("policy_recall") is not None and x["policy_recall"] < x["recall"]]
print("Total:", len(data), "Degraded:", len(degraded))
for item in degraded:
    print("ID:", item["id"])
    print("Q:", item["question"])
    print("recall:", item["recall"], "->", item["policy_recall"])
    print("expected:", item["expected_retrievers"])
    print("llm:", item["llm_candidates"])
    print("policy:", item["policy_retrievers"])
    print("policy_missing:", item["policy_missing"])
    print("rejected:", item["rejected_tools"])
    print("intervened:", item["policy_intervened"])
