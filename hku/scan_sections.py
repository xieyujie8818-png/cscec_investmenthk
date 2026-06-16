import zipfile, re, xml.etree.ElementTree as ET
from pathlib import Path

base = Path(r"C:\Users\yujie.xie\.cursor\cohl-marketing\hku\Technical Submission")

def extract_paras(p):
    with zipfile.ZipFile(p) as z:
        root = ET.fromstring(z.read("word/document.xml"))
    WNS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
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

files = sorted(base.glob("*.docx"))
files = [f for f in files if not f.name.startswith("~$") and "backup" not in f.name.lower()]

out = []
out.append(f"Found {len(files)} docx files\n")
for f in files:
    try:
        paras = extract_paras(f)
        out.append("=" * 80)
        out.append(f"FILE: {f.name}")
        out.append("First 10 paragraphs:")
        for j, p in enumerate(paras[:10]):
            out.append(f"  [{j}] {p[:300]}")
    except Exception as e:
        out.append(f"ERROR {f.name}: {e}")

result = "\n".join(out)
Path(r"C:\Users\yujie.xie\.cursor\cohl-marketing\hku\section_scan_result.txt").write_text(result, encoding="utf-8")
print(result)
