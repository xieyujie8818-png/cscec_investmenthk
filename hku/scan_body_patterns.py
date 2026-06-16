import zipfile, re, xml.etree.ElementTree as ET
from pathlib import Path

base = Path(r"C:\Users\yujie.xie\.cursor\cohl-marketing\hku\Technical Submission")
WNS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

def full_text(p):
    with zipfile.ZipFile(p) as z:
        root = ET.fromstring(z.read("word/document.xml"))
    return "".join((t.text or "") + (t.tail or "") for t in root.iter(WNS + "t"))

checks = [
    ("4 (ii) with space", r"4\s+\(ii\)"),
    ("and(iii)", r"and\s*\(iii\)", re.I),
    ("4(ii)(iii) no ampersand", r"4\s*\(ii\)\s*\(iii\)"),
    ("em/en dash", r"[—–]"),
    ("Section hyphen title", r"Section\s+[\d\(\)a-z&\s]+\s-\s"),
]

files = sorted(
    f for f in base.glob("*.docx")
    if not f.name.startswith("~") and "backup" not in f.name.lower()
)
for f in files:
    t = full_text(f)
    hits = []
    for item in checks:
        label, pat = item[0], item[1]
        flags = item[2] if len(item) > 2 else 0
        m = re.findall(pat, t, flags)
        if m:
            # show first example context
            ctx = re.search(pat, t, flags)
            snippet = t[max(0, ctx.start() - 20) : ctx.end() + 40].replace("\n", " ")
            hits.append(f"{label} x{len(m)} e.g. ...{snippet[:80]}...")
    print(f.name)
    print("  " + ("\n  ".join(hits) if hits else "clean for checked patterns"))
