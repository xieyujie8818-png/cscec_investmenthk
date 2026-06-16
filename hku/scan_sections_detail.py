import zipfile, re, xml.etree.ElementTree as ET
from pathlib import Path

base = Path(r"C:\Users\yujie.xie\.cursor\cohl-marketing\hku\Technical Submission")
WNS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

def extract_paras(p):
    with zipfile.ZipFile(p) as z:
        root = ET.fromstring(z.read("word/document.xml"))
    paras = []
    for para in root.iter(WNS + "p"):
        parts = []
        for t in para.iter(WNS + "t"):
            if t.text:
                parts.append(t.text)
            if t.tail:
                parts.append(t.tail)
        text = "".join(parts).strip()
        if text:
            paras.append(text)
    return paras

section_re = re.compile(r"Section\s+[\d\(\)a-z&\s\-—–]+", re.I)

files = sorted(
    f for f in base.glob("*.docx")
    if not f.name.startswith("~") and "backup" not in f.name.lower()
)

lines = []
for f in files:
    paras = extract_paras(f)
    section_lines = [(i, p) for i, p in enumerate(paras[:20]) if "section" in p.lower() or re.search(r"^4\s*\(|^5\s*\(", p, re.I)]
    lines.append(f"\n{'='*70}")
    lines.append(f"FILE: {f.name}")
    lines.append("FILENAME ISSUES:")
    name = f.name
    fname_issues = []
    if re.search(r"\(b\)Job|\(b\)CV|\(iii\)CV", name):
        fname_issues.append("missing space after section code before next word")
    if "and(iii)" in name.lower():
        fname_issues.append("uses 'and' instead of '&'")
    if re.search(r"4\s*\(ii\)", name) and "&" not in name and "and" not in name.lower():
        fname_issues.append("4(ii)(iii) without '&' between (ii) and (iii)")
    if re.search(r"4\s+\(ii\)", name):
        fname_issues.append("extra space: '4 (ii)' instead of '4(ii)'")
    lines.append("  " + ("; ".join(fname_issues) if fname_issues else "none detected"))

    lines.append("OPENING HEADER BLOCK (paras 0-5):")
    for i in range(min(6, len(paras))):
        lines.append(f"  [{i}] {paras[i][:200]}")

    lines.append("ALL Section-related lines (first 20 paras):")
    for i, p in section_lines:
        marker = ""
        if "—" in p or "–" in p:
            marker = " [HAS EM/EN DASH]"
        elif " - " in p or p.endswith("-"):
            marker = " [HAS HYPHEN]"
        if re.search(r"4\s+\(ii\)", p):
            marker += " [SPACE BEFORE (ii)]"
        if "and(iii)" in p.lower() or "and (iii)" in p.lower():
            marker += " [uses AND not &]"
        if re.search(r"4\(ii\)\(iii\)", p.replace(" ", "")):
            marker += " [no & between ii and iii]"
        lines.append(f"  [{i}] {p[:220]}{marker}")

    # check combined format
    combined = False
    for p in paras[:10]:
        if re.search(r"Section\s+4\(i\)\(b\)\s*[—–\-]", p):
            combined = True
        if re.search(r"Section\s+4\(ii\)\s*&\s*\(iii\)\s*[—–\-]", p):
            combined = True
        if re.search(r"Section\s+5\(i\)\s*[—–\-]", p):
            combined = True
    lines.append(f"USES COMBINED 'Section X — Title' FORMAT: {combined}")

result = "\n".join(lines)
out = Path(r"C:\Users\yujie.xie\.cursor\cohl-marketing\hku\section_detail.txt")
out.write_text(result, encoding="utf-8")
print(result)
