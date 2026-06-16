import zipfile
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from difflib import SequenceMatcher

WNS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
job_path = Path(
    r"C:\Users\yujie.xie\.cursor\cohl-marketing\hku\Technical Submission"
    r"\1.0 4(i)(b) Job Reference of C-Living.docx"
)
cv_path = Path(
    r"C:\Users\yujie.xie\.cursor\cohl-marketing\hku\Technical Submission"
    r"\1.0 4(ii)(iii) CV of C-Living.docx"
)


def wtag(name):
    return f"{WNS}{name}"


def extract_paras(path):
    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read("word/document.xml"))
    paras = []
    for p in root.iter(wtag("p")):
        text = "".join(
            (t.text or "") + (t.tail or "") for t in p.iter(wtag("t"))
        ).strip()
        if text:
            paras.append(text)
    return paras


def parse_projects(paras):
    projects = []
    current = None
    field_re = re.compile(
        r"^(Project:|Project Description$|Project Type:|Project Cost:|Completion:|Client:|Parent Company:|Period:|Employer:|Details of awards)"
    )
    for t in paras:
        if t == "Project:":
            if current:
                projects.append(current)
            current = {"name": None, "fields": {}, "description_parts": []}
            continue
        if current is None:
            continue
        if current["name"] is None and not field_re.match(t):
            current["name"] = t
            continue
        if t == "Project Description":
            current["mode"] = "desc"
            continue
        m = re.match(r"^(Project Type:|Project Cost:|Completion:|Client:|Parent Company:)$", t)
        if m:
            current["pending_field"] = m.group(1)
            current["mode"] = "field"
            continue
        if t.startswith("Details of awards"):
            current["fields"]["Details of awards"] = "(label only, value next para)"
            current["pending_field"] = "Details of awards value"
            current["mode"] = "field"
            continue
        if current.get("mode") == "desc":
            current["description_parts"].append(t)
        elif current.get("pending_field"):
            key = current["pending_field"]
            current["fields"][key.rstrip(" value")] = t
            current["pending_field"] = None
    if current:
        projects.append(current)
    return projects


job_paras = extract_paras(job_path)
cv_paras = extract_paras(cv_path)
projects = parse_projects(job_paras)
cv_text = "\n".join(cv_paras)

lines = []
lines.append("=== PER-PROJECT FIELD MATRIX ===")
all_fields = set()
for p in projects:
    all_fields.update(p["fields"].keys())
for i, p in enumerate(projects, 1):
    lines.append(f"\nProject {i}: {p['name']}")
    lines.append(f"  Description paras: {len(p['description_parts'])}")
    desc = " ".join(p["description_parts"])
    lines.append(f"  Desc length: {len(desc)} chars")
    for f in sorted(all_fields):
        val = p["fields"].get(f, "— MISSING —")
        lines.append(f"  {f}: {val}")

lines.append("\n=== GRAMMAR / TYPO SCAN ===")
full = "\n".join(job_paras)
typos = [
    ("locate at (should be located)", r"\bis locate at\b"),
    ("500million (no space)", r"500million"),
    ("HK\\$ 500", r"HK\$ ?500"),
    ("comma splice / run-on", r"Ho Man Tin, is built"),
    ("Ltd\\(688\\) no space", r"Ltd\(688\)"),
    ("Ltd\\(688\\) missing space before paren", r"Ltd\(688\)"),
    ("orphan sentence fragment", r"^construction, sales, and marketing"),
    ("smart/curly quotes", r"[\u2018\u2019\u201c\u201d]"),
    ("encoding garble", r"Beijing.{0,3}s old"),
    ("double space", r"  +"),
    ("slash spacing inconsistent", r"/ "),
]
for label, pat in typos:
    for m in re.finditer(pat, full, re.I | re.M):
        snippet = full[max(0, m.start() - 30) : m.end() + 50].replace("\n", " ")
        lines.append(f"  {label}: ...{snippet[:120]}...")

lines.append("\n=== PROJECT TYPE VALUES ===")
for i, p in enumerate(projects, 1):
    lines.append(f"  P{i}: {p['fields'].get('Project Type:', 'MISSING')}")

lines.append("\n=== AWARDS VALUES ===")
for i, p in enumerate(projects, 1):
    lines.append(f"  P{i}: {p['fields'].get('Details of awards', 'MISSING')}")

lines.append("\n=== CV DUPLICATE CHECK (same discipline PM) ===")
cv_file = cv_path.name
for p in projects:
    name = p["name"] or ""
    key = name.split(",")[0].strip()[:20]
    if key and key.lower() in cv_text.lower():
        # get cv block
        idx = cv_text.lower().find(name.lower()[:15])
        job_desc = " ".join(p["description_parts"])[:500]
        if idx >= 0:
            cv_chunk = cv_text[idx : idx + len(job_desc) + 200]
            ratio = SequenceMatcher(
                None,
                re.sub(r"\s+", " ", job_desc.lower()),
                re.sub(r"\s+", " ", cv_chunk.lower()[: len(job_desc)]),
            ).ratio()
            lines.append(f"  {name}: CV overlap ~{ratio*100:.1f}%")
        else:
            lines.append(f"  {name}: found in CV by partial match")
    else:
        lines.append(f"  {name}: not clearly matched in CV")

lines.append("\n=== STRUCTURAL / FORMAT NOTES ===")
lines.append(f"  Discipline header: {[p for p in job_paras if p in ('5.0','Project Management')]}")
lines.append(f"  File prefix says 1.0 but body says 5.0 Project Management")
lines.append(f"  Header lines 1-4: {job_paras[:4]}")
lines.append(f"  Empty para gaps: indices jump (para 4-5 missing in first block)")

# Project 3 fragment
for i, t in enumerate(job_paras):
    if t.startswith("construction, sales"):
        lines.append(f"  Orphan fragment at para index {i}: {t[:100]}")

# Check awards empty
for i, p in enumerate(projects, 1):
    awards = p["fields"].get("Details of awards", "")
    if not awards or awards in ("N/A", "(label only, value next para)"):
        lines.append(f"  Project {i} awards empty or N/A")

out = Path(r"C:\Users\yujie.xie\.cursor\cohl-marketing\hku\cliving_deep.txt")
out.write_text("\n".join(lines), encoding="utf-8")
print("\n".join(lines))
