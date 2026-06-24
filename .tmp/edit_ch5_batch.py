import re
from pathlib import Path

path = Path(
    r"G:\Agentic GraphRAG Chatbot luật"
    r"\ĐATN_20225919_Lê_Thái_Sơn_Chatbot_tư_vấn_luật_hôn_nhân_gia_đình"
    r"\Chuong\5_Giai_phap_dong_gop.tex"
)
lines = path.read_text(encoding="utf-8").splitlines(keepends=True)

# 1) Remove \texttt{...}
text = "".join(lines)
text, _ = re.subn(r"\\texttt\{([^}]*)\}", lambda m: re.sub(r"(?<!\\)_", r"\\_", m.group(1)), text)

# 2) Comment retriever cap_duong .. xu_phat_vi_pham
out_lines = []
in_comment_block = False
for line in text.splitlines(keepends=True):
    stripped = line.lstrip()
    if stripped.startswith(r"\paragraph{Retriever cap\_duong."):
        in_comment_block = True
    if in_comment_block:
        if not stripped.startswith("%"):
            line = "% " + line if line.strip() else line
        if stripped.startswith(r"\paragraph{Retriever xu\_phat\_vi\_pham."):
            # comment this line and the following content line, then exit block after next non-empty
            pass
    if in_comment_block and stripped.startswith("Retriever này bao quát") and "xu\_phat" in "".join(out_lines[-2:]):
        out_lines.append(line if line.startswith("%") else "% " + line)
        in_comment_block = False
        continue
    out_lines.append(line)

text = "".join(out_lines)

# Fix comment block more reliably with regex
start = text.find(r"\paragraph{Retriever cap\_duong.}")
end_marker = "xui\_giuc\_cuong\_ep\_bao\_luc.\n"
end = text.find(end_marker, start)
if start != -1 and end != -1:
    end = end + len(end_marker)
    block = text[start:end]
    commented = "".join(
        ("% " + ln if ln.strip() and not ln.lstrip().startswith("%") else ln)
        for ln in block.splitlines(keepends=True)
    )
    text = text[:start] + commented + text[end:]

# 3) Benchmark: subsection -> section, subsubsection -> subsection
text = text.replace(
    r"\subsection{Xây dựng tập Benchmark đánh giá hệ thống tư vấn pháp luật}",
    r"\section{Xây dựng tập Benchmark đánh giá ứng dụng}",
)
text = text.replace(r"\label{subsection:benchmark}", r"\label{section:benchmark}")
for old in [
    r"\subsubsection{Thu thập dữ liệu}",
    r"\subsubsection{Cấu trúc mẫu dữ liệu trong tập benchmark}",
    r"\subsubsection{Quy trình hiệu chỉnh và gán nhãn thủ công}",
    r"\subsubsection{Thiết kế test case cho các trường hợp ngoại lệ}",
]:
    text = text.replace(old, old.replace(r"\subsubsection{", r"\subsection{"))

R = r">{\raggedright\arraybackslash}"

# 4) Intent table: widen Template column
text = text.replace(
    rf"\begin{{tabularx}}{{\textwidth}}{{|{R}p{{2.6cm}}|{R}p{{3.6cm}}|{R}X|}}",
    rf"\begin{{tabularx}}{{\textwidth}}{{|{R}p{{2.4cm}}|{R}p{{4.2cm}}|{R}X|}}",
    1,
)

# 5) Nodes table: widen label column + hyphenate long labels
text = text.replace(
    rf"\begin{{tabularx}}{{\textwidth}}{{|{R}p{{2.1cm}}|{R}p{{2.0cm}}|{R}p{{3.1cm}}|{R}X|}}",
    rf"\begin{{tabularx}}{{\textwidth}}{{|{R}p{{2.5cm}}|{R}p{{1.9cm}}|{R}p{{3.0cm}}|{R}X|}}",
    1,
)
label_fixes = [
    ("ChePhapDoTaiSan &", "ChePhap\\-DoTai\\-San &"),
    ("LoaiTaiSan &", "Loai\\-Tai\\-San &"),
    ("TruongHopNgoaiLe &", "TruongHop\\-Ngoai\\-Le &"),
    ("VanBanPhapLy &", "VanBan\\-Phap\\-Ly &"),
    ("ThoaThuan &", "Thoa\\-Thuan &"),
    ("DieuKien &", "Dieu\\-Kien &"),
    ("HauQua &", "Hau\\-Qua &"),
    ("HanhVi &", "Hanh\\-Vi &"),
    ("NghiaVu &", "Nghia\\-Vu &"),
]
for old, new in label_fixes:
    text = text.replace(old, new, 1)

# ThoaThuan attributes: add newline in col3
text = text.replace(
    "yeu\\_\\allowbreak cau\\_\\allowbreak van\\_\\allowbreak ban, yeu\\_\\allowbreak cau\\_\\allowbreak cong\\_\\allowbreak chung, yeu\\_\\allowbreak cau\\_\\allowbreak chung\\_\\allowbreak thuc, thoi\\_\\allowbreak diem\\_\\allowbreak lap, co\\_\\allowbreak the\\_\\allowbreak sua\\_\\allowbreak doi &",
    "yeu\\_\\allowbreak cau\\_\\allowbreak van\\_\\allowbreak ban, yeu\\_\\allowbreak cau\\_\\allowbreak cong\\_\\allowbreak chung, \\newline yeu\\_\\allowbreak cau\\_\\allowbreak chung\\_\\allowbreak thuc, thoi\\_\\allowbreak diem\\_\\allowbreak lap, co\\_\\allowbreak the\\_\\allowbreak sua\\_\\allowbreak doi &",
)

path.write_text(text, encoding="utf-8", newline="\n")
print("texttt:", len(re.findall(r"\\texttt", text)))
print("done")
