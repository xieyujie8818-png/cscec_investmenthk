import zipfile
import re
import xml.etree.ElementTree as ET
from pathlib import Path

WNS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
base = Path(r"C:\Users\yujie.xie\.cursor\cohl-marketing\hku\Technical Submission")


def text(p):
    with zipfile.ZipFile(p) as z:
        root = ET.fromstring(z.read("word/document.xml"))
    return "".join((t.text or "") + (t.tail or "") for t in root.iter(WNS + "t"))


cv = text(base / "1.0 4(ii)(iii) CV of C-Living.docx")
print("=== C-Living CV ===")
print("refs:", re.findall(r"Please refer to Section 4\(i\)\(b\)[^\n]{0,200}", cv))
for kw in ["21 Valley", "Two Victoria", "One Victoria", "Guanchen", "Huabichang", "5.0", "1.0 Project"]:
    i = cv.find(kw)
    print(kw, "at", i if i >= 0 else "NOT FOUND")

jr = text(base / "1.0 4(i)(b) Job Reference of C-Living.docx")
print("\n=== C-Living Job Ref fixes ===")
checks = [
    ("500 million spaced", "HK$ 500 million" in jr),
    ("grammar P1 located", "is located at 15-21" in jr),
    ("locate typo gone", "is locate at" not in jr),
    ('CSCI quotes fixed', '"CSCI" or the' in jr),
    ("orphan fragment remains", "construction, sales, and marketing. By synergizing" in jr),
    ("Parent Company field", "Parent Company:" in jr),
]
for label, val in checks:
    print(f"  {label}: {val}")
print("  Not available count:", jr.count("Not available"))

bs = text(base / "4.0 4(ii)(iii) CV of BS 20260605.docx")
print("\n=== BS CV ===")
print(re.findall(r"Please refer[^\n]{0,200}", bs)[:3])
for kw in ["LST", "Victoria Skye", "Heritage", "Hotel Jen"]:
    print(f"  {kw} in CV:", kw.lower() in bs.lower())

cop_cv = text(base / "6.0 4(ii)(iii) CV of COPSL v2.docx")
print("\n=== COPSL CV refs ===", len(re.findall(r"Please refer", cop_cv)))

cwn = [p for p in base.glob("2.0 4(ii)(iii) CV of CWN*") if "backup" not in p.name.lower()][0]
cwn_t = text(cwn)
print("\n=== CWN CV refs (all) ===")
for r in re.findall(r"Please refer to Section 4\(i\)\(b\)[^\n]{0,220}", cwn_t):
    print(" ", r[:180])
