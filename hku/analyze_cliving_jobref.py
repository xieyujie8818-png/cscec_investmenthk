import zipfile
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import Counter

WNS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
path = Path(
    r"C:\Users\yujie.xie\.cursor\cohl-marketing\hku\Technical Submission"
    r"\1.0 4(i)(b) Job Reference of C-Living.docx"
)


def wtag(name):
    return f"{WNS}{name}"


def para_text(p):
    parts = []
    for t in p.iter(wtag("t")):
        if t.text:
            parts.append(t.text)
        if t.tail:
            parts.append(t.tail)
    return "".join(parts)


def get_para_style(p):
    ppr = p.find(wtag("pPr"))
    if ppr is None:
        return ""
    style = ppr.find(wtag("pStyle"))
    if style is not None and style.get(wtag("val")):
        return style.get(wtag("val"))
    return ""


def get_run_info(p):
    runs = []
    for r in p.findall(wtag("r")):
        rpr = r.find(wtag("rPr"))
        bold = rpr is not None and rpr.find(wtag("b")) is not None
        texts = [t.text or "" for t in r.findall(wtag("t"))]
        if texts:
            runs.append({"text": "".join(texts), "bold": bold})
    return runs


with zipfile.ZipFile(path) as z:
    root = ET.fromstring(z.read("word/document.xml"))

paras = []
for i, p in enumerate(root.iter(wtag("p"))):
    text = para_text(p).strip()
    if not text:
        continue
    paras.append(
        {
            "idx": i,
            "text": text,
            "style": get_para_style(p),
            "runs": get_run_info(p),
        }
    )

# Output
lines = []
lines.append(f"TOTAL NON-EMPTY PARAS: {len(paras)}")
lines.append("\n=== FIRST 25 PARAGRAPHS ===")
for p in paras[:25]:
    bold = any(r["bold"] for r in p["runs"])
    lines.append(
        f"[{p['idx']}] style={p['style']!r} bold={bold} | {p['text'][:300]}"
    )

# Projects
lines.append("\n=== PROJECT BLOCKS ===")
project_idxs = [i for i, p in enumerate(paras) if p["text"].startswith("Project:")]
for n, pi in enumerate(project_idxs, 1):
    end = project_idxs[n] if n < len(project_idxs) else len(paras)
    block = paras[pi:end]
    lines.append(f"\n--- Project {n} ---")
    for p in block[:15]:
        lines.append(f"  {p['text'][:250]}")
    if len(block) > 15:
        lines.append(f"  ... ({len(block)} paras total)")

# Field labels scan
full = "\n".join(p["text"] for p in paras)
labels = [
    "Project:",
    "Project Description",
    "Project Type:",
    "Project Cost:",
    "Completion:",
    "Client:",
    "Period:",
    "Employer:",
    "Contract Period:",
    "Annual Conntract",
    "Annual Contract",
    "Number of Rooms:",
    "Details of awards",
]
lines.append("\n=== LABEL COUNTS ===")
for lb in labels:
    c = full.count(lb)
    lines.append(f"  {lb}: {c}")

# Typos / patterns
lines.append("\n=== PATTERN CHECKS ===")
checks = [
    ("Conntract typo", r"Conntract"),
    ("double spaces", r"  +"),
    ("Section 4(i) standalone", r"^Section 4\(i\)$"),
    ("missing em dash header", r"Section 4\(i\)\(b\)\s*[—–]"),
    ("Corporate Profile in header area", r"^Corporate Profile$"),
    ("inconsistent HKD/HK$", r"HK\$|HKD"),
    ("smart quote issues", r"[\u2018\u2019\u201c\u201d]"),
]
for name, pat in checks:
    m = re.findall(pat, full, re.M)
    if m:
        lines.append(f"  {name}: {len(m)} hit(s)")

# Compare project count
lines.append(f"\nProject count: {len(project_idxs)}")

# Discipline headers
lines.append("\n=== DISCIPLINE / SECTION MARKERS ===")
for p in paras[:30]:
    t = p["text"]
    if re.match(r"^\d+\.0$", t) or t.startswith("Section ") or t in (
        "Project Management",
        "Corporate Profile",
    ):
        lines.append(f"  [{p['idx']}] {t}")

out = Path(r"C:\Users\yujie.xie\.cursor\cohl-marketing\hku\cliving_jobref_analysis.txt")
out.write_text("\n".join(lines), encoding="utf-8")
print("\n".join(lines))
