import pandas as pd
import json
import glob
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

columns_to_drop = [
    "legal_citation_accuracy",
    "legal_validity_accuracy",
    "citation_prioritization_accuracy",
    "invalid_citation_rate",
    "context_conflict_detection_rate",
    "hallucination_rate",
    "faithfulness",
    "context_recall",
    "answer_correctness",
    "chatbot_answer",
    "dieu_khoan_ap_dung",
]

csv_files = glob.glob(os.path.join(os.path.dirname(__file__), "*.csv"))

for csv_path in csv_files:
    df = pd.read_csv(csv_path)
    print(f"Processing: {csv_path}")
    print(f"  Columns before: {list(df.columns)}")

    cols_existing = [c for c in columns_to_drop if c in df.columns]
    df.drop(columns=cols_existing, inplace=True)
    print(f"  Dropped: {cols_existing}")
    print(f"  Columns after: {list(df.columns)}")

    df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    json_path = os.path.splitext(csv_path)[0] + ".json"
    records = df.to_dict(orient="records")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    print(f"  Saved JSON: {json_path}\n")

print("Done!")
