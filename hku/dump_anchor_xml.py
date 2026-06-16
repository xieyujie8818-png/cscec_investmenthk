import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

WNS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
WP = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"

base = Path(r"C:\Users\yujie.xie\.cursor\cohl-marketing\hku\Technical Submission")
cv = [p for p in base.glob("2.0 4(ii)(iii) CV of CWN*") if "backup" not in p.name.lower()][0]

with zipfile.ZipFile(cv) as z:
    root = ET.fromstring(z.read("word/document.xml"))

body = root.find(f"{{{WNS}}}body")
tables = [el for el in body if el.tag == f"{{{WNS}}}tbl"]
# index 2 = fan garden (body 68 was index in body list, not tables list)
# project tables are indices 2,3,4,5,6 in tables list from earlier (index#2-6)

for ti in [2, 3, 4, 6]:  # skip 5 = A22102
    tbl = tables[ti]
    rows = tbl.findall(f"{{{WNS}}}tr")
    tr = rows[1]
    tc = tr.findall(f"{{{WNS}}}tc")[0]
    print(f"\n===== TABLE {ti} ROW 1 CELL 0 =====")
    for pi, p in enumerate(list(tc.findall(f"{{{WNS}}}p"))[:3]):
        print(f"--- para {pi} ---")
        anchors = list(p.iter(f"{{{WP}}}anchor"))
        if anchors:
            for ai, a in enumerate(anchors):
                ext = a.find(f"{{{WP}}}extent")
                posH = a.find(f"{{{WP}}}positionH")
                posV = a.find(f"{{{WP}}}positionV")
                print(f"  anchor {ai}: cx={ext.get('cx')} cy={ext.get('cy')}")
                if posH is not None:
                    print(f"    posH: {ET.tostring(posH, encoding='unicode')[:200]}")
                if posV is not None:
                    print(f"    posV: {ET.tostring(posV, encoding='unicode')[:200]}")
        else:
            txt = "".join((t.text or "") + (t.tail or "") for t in p.iter(f"{{{WNS}}}t")).strip()
            print(f"  empty/text: {txt!r}")
