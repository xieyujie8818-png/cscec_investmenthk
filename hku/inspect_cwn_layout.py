import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

WNS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
WP = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
PIC = "http://schemas.openxmlformats.org/drawingml/2006/picture"
RNS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

EMU_PER_CM = 360000


def wtag(n):
    return f"{{{WNS}}}{n}"


def cell_text(tc):
    return "".join((t.text or "") + (t.tail or "") for t in tc.iter(wtag("t"))).strip()


def para_text(p):
    return "".join((t.text or "") + (t.tail or "") for t in p.iter(wtag("t"))).strip()


def get_image_sizes(tc):
    sizes = []
    for inline in tc.iter(f"{{{WP}}}inline"):
        ext = inline.find(f"{{{WP}}}extent")
        if ext is not None:
            cx = int(ext.get("cx", 0))
            cy = int(ext.get("cy", 0))
            sizes.append((cx, cy, cx / EMU_PER_CM, cy / EMU_PER_CM))
    return sizes


base = Path(r"C:\Users\yujie.xie\.cursor\cohl-marketing\hku\Technical Submission")
cv = [p for p in base.glob("2.0 4(ii)(iii) CV of CWN*") if "backup" not in p.name.lower()][0]

with zipfile.ZipFile(cv) as z:
    root = ET.fromstring(z.read("word/document.xml"))

body = root.find(wtag("body"))
tables = []
for i, el in enumerate(list(body)):
    if el.tag == wtag("tbl"):
        tables.append((i, el))

print(f"FILE: {cv.name}")
print(f"Total body tables: {len(tables)}\n")

for ti, (bi, tbl) in enumerate(tables):
    rows = tbl.findall(wtag("tr"))
    first_text = ""
    for tr in rows:
        for tc in tr.findall(wtag("tc")):
            t = cell_text(tc)
            if t:
                first_text = t[:80]
                break
        if first_text:
            break

    if not any(
        k in first_text
        for k in [
            "Project",
            "Fan Garden",
            "Greenhill",
            "Wan Chai",
            "A22102",
            "B1203",
            "Ching",
            "Staff",
            "Qualification",
            "Duties",
            "Organization",
            "KEY PERSON",
            "Please refer",
        ]
    ):
        continue

    print(f"=== TABLE body[{bi}] index#{ti} rows={len(rows)} ===")
    print(f"  First: {first_text}")
    for ri, tr in enumerate(rows):
        tr_pr = tr.find(wtag("trPr"))
        tr_h = tr_pr.find(wtag("trHeight")) if tr_pr is not None else None
        h_val = tr_h.get(wtag("val")) if tr_h is not None else None
        cells_info = []
        for ci, tc in enumerate(tr.findall(wtag("tc"))):
            txt = cell_text(tc)[:60]
            imgs = get_image_sizes(tc)
            paras = [para_text(p) for p in tc.findall(wtag("p")) if para_text(p)]
            cells_info.append(
                {
                    "text": txt,
                    "paras": len(paras),
                    "empty_paras": sum(1 for p in tc.findall(wtag("p")) if not para_text(p)),
                    "imgs": imgs,
                }
            )
        row_desc = []
        for ci, c in enumerate(cells_info):
            parts = []
            if c["text"]:
                parts.append(f"text={c['text'][:50]!r}")
            if c["imgs"]:
                parts.append(
                    "imgs="
                    + ", ".join(f"{w:.1f}x{h:.1f}cm" for _, _, w, h in c["imgs"])
                )
            if c["empty_paras"]:
                parts.append(f"empty_p={c['empty_paras']}")
            if parts:
                row_desc.append(f"c{ci}:" + " ".join(parts))
            elif c["paras"] == 0 and not c["imgs"]:
                row_desc.append(f"c{ci}:EMPTY")
        if row_desc:
            h_info = f" trH={h_val}" if h_val else ""
            print(f"  r{ri}{h_info}: {' | '.join(row_desc)}")
    print()

# empty paragraphs between tables in project section
all_p = list(root.iter(wtag("p")))
empty_ranges = []
empty_count = 0
for pi, p in enumerate(all_p):
    t = para_text(p)
    if not t:
        empty_count += 1
    else:
        if empty_count >= 5:
            empty_ranges.append((pi - empty_count, pi - 1, empty_count))
        empty_count = 0

print("=== LARGE EMPTY PARAGRAPH GAPS (>=5 consecutive) ===")
for start, end, n in empty_ranges[:15]:
    # context
    before = para_text(all_p[start - 1])[:60] if start > 0 else ""
    after = para_text(all_p[end + 1])[:60] if end + 1 < len(all_p) else ""
    print(f"  p{start}-{end} ({n} empty) after:{before!r} before:{after!r}")
