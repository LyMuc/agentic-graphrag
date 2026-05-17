"""
Recovery script: restore chu_de_phap_ly from Cursor Local History versions.

For each (file -> best_version) pair in MAPPING:
  1. Replace the JSON file in benchmark/ with the history version
  2. Sync the chu_de_phap_ly column back into the matching CSV file
     (matched by 'question' column, falling back to row order if needed)

A backup of the current state was made before running this script.
"""

import json
import os
import sys
import shutil
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

BENCH_DIR = os.path.dirname(os.path.abspath(__file__))

# (json_file_name, absolute_path_to_history_version, expected_filled_count)
MAPPING = [
    ("qa_cham_dut_hon_nhan_do_vo_chong_chet.json",
     r"C:\Users\Admin\AppData\Roaming\Cursor\User\History\-2cd8695f\7L3G.json", 2),
    ("qa_che_do_tai_san_cua_vo_chong.json",
     r"C:\Users\Admin\AppData\Roaming\Cursor\User\History\6481952f\rj2c.json", 24),
    ("qa_dieu_kien_ket_hon.json",
     r"C:\Users\Admin\AppData\Roaming\Cursor\User\History\60e2bff\z1SH.json", 45),
    ("qa_giai_quyet_no_chung_khi_ly_hon.json",
     r"C:\Users\Admin\AppData\Roaming\Cursor\User\History\-40fdb3d3\1kdM.json", 8),
    ("qa_ket_hon_trai_phap_luat.json",
     r"C:\Users\Admin\AppData\Roaming\Cursor\User\History\-283e4d1f\gnAO.json", 11),
    ("qa_nghia_vu_cap_duong.json",
     r"C:\Users\Admin\AppData\Roaming\Cursor\User\History\3045a437\0HDc.json", 8),
    ("qa_quan_he_hon_nhan.json",
     r"C:\Users\Admin\AppData\Roaming\Cursor\User\History\-119e5ba\jDc1.json", 8),
    ("qa_quy_dinh_chung_khai_niem_phap_ly.json",
     r"C:\Users\Admin\AppData\Roaming\Cursor\User\History\-7dd9631e\mnDG.json", 9),
    ("qa_song_chung_nhu_vo_chong.json",
     r"C:\Users\Admin\AppData\Roaming\Cursor\User\History\50beaf72\3rRw.json", 1),
    ("qa_tai_san_chung_cua_vo_chong.json",
     r"C:\Users\Admin\AppData\Roaming\Cursor\User\History\-7329a8c\06xV.json", 9),
    ("qa_thuan_tinh_ly_hon.json",
     r"C:\Users\Admin\AppData\Roaming\Cursor\User\History\7dde3f9f\iaiV.json", 4),
]


def is_filled(value) -> bool:
    if value is None:
        return False
    s = str(value).strip()
    return s != "" and s.lower() != "nan"


def restore_one(json_name: str, history_path: str, expected_filled: int) -> dict:
    target_json = os.path.join(BENCH_DIR, json_name)
    csv_name = os.path.splitext(json_name)[0] + ".csv"
    target_csv = os.path.join(BENCH_DIR, csv_name)

    if not os.path.exists(history_path):
        return {"file": json_name, "status": "FAIL", "reason": f"history not found: {history_path}"}

    with open(history_path, "r", encoding="utf-8") as f:
        history_records = json.load(f)
    if not isinstance(history_records, list):
        history_records = [history_records]

    actual_filled = sum(
        1 for r in history_records if is_filled(r.get("chu_de_phap_ly"))
    )
    if actual_filled != expected_filled:
        print(
            f"  WARNING: {json_name} expected {expected_filled} filled but found {actual_filled}"
        )

    shutil.copy2(history_path, target_json)

    csv_status = "csv-skipped"
    if os.path.exists(target_csv):
        try:
            df = pd.read_csv(target_csv)
            if "chu_de_phap_ly" not in df.columns:
                df["chu_de_phap_ly"] = ""
            df["chu_de_phap_ly"] = df["chu_de_phap_ly"].astype(object)
            df.loc[df["chu_de_phap_ly"].isna(), "chu_de_phap_ly"] = ""

            hist_by_q = {}
            for r in history_records:
                q = r.get("question")
                if q is not None and is_filled(r.get("chu_de_phap_ly")):
                    hist_by_q[str(q).strip()] = r["chu_de_phap_ly"]

            updated_rows = 0
            if "question" in df.columns and hist_by_q:
                for idx, row in df.iterrows():
                    q = str(row.get("question", "")).strip()
                    if q in hist_by_q:
                        df.at[idx, "chu_de_phap_ly"] = hist_by_q[q]
                        updated_rows += 1
                csv_status = f"csv-updated-by-question ({updated_rows}/{len(df)})"
            else:
                n = min(len(df), len(history_records))
                for i in range(n):
                    val = history_records[i].get("chu_de_phap_ly")
                    if is_filled(val):
                        df.at[i, "chu_de_phap_ly"] = val
                        updated_rows += 1
                csv_status = f"csv-updated-by-index ({updated_rows}/{len(df)})"

            df.to_csv(target_csv, index=False, encoding="utf-8-sig")
        except Exception as e:
            csv_status = f"csv-error: {e}"

    return {
        "file": json_name,
        "status": "OK",
        "json_filled": actual_filled,
        "json_total": len(history_records),
        "csv": csv_status,
    }


def main() -> None:
    print(f"Restoring {len(MAPPING)} files from Cursor Local History\n")
    results = []
    for name, hist, expected in MAPPING:
        print(f"-> {name}")
        res = restore_one(name, hist, expected)
        results.append(res)
        if res["status"] == "OK":
            print(
                f"   JSON: {res['json_filled']}/{res['json_total']} filled  |  {res['csv']}"
            )
        else:
            print(f"   FAILED: {res.get('reason')}")
        print()

    print("=" * 70)
    ok = sum(1 for r in results if r["status"] == "OK")
    print(f"Recovered {ok}/{len(results)} files successfully")


if __name__ == "__main__":
    main()
