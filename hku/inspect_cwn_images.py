import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

WNS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
WP = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
VML = "urn:schemas-microsoft-com:vml"
EMU = 360000

base = Path(r"C:\Users\yujie.xie\.cursor\cohl-marketing\hku\Technical Submission")
cv = [p for p in base.glob("2.0 4(ii)(iii) CV of CWN*") if "backup" not in p.name.lower()][0]

with zipfile.ZipFile(cv) as z:
    xml = z.read("word/document.xml")
    root = ET.fromstring(xml)
    media = [n for n in z.namelist() if n.startswith("word/media/")]

print("Media files:", len(media))
for m in media[:20]:
    print(" ", m)

print("\nDrawing counts in full doc:")
print("  wp:inline", xml.count(b"wp:inline"))
print("  wp:anchor", xml.count(b"wp:anchor"))
print("  v:imagedata", xml.count(b"v:imagedata"))
print("  a:blip", xml.count(b"a:blip"))


def wtag(n):
    return f"{{{WNS}}}{n}"


def find_images_in_element(el, label):
    for inline in el.iter(f"{{{WP}}}inline"):
        ext = inline.find(f"{{{WP}}}extent")
        cx = int(ext.get("cx", 0)) if ext is not None else 0
        cy = int(ext.get("cy", 0)) if ext is not None else 0
        print(f"  {label} inline: {cx/EMU:.2f}x{cy/EMU:.2f} cm")
    for anchor in el.iter(f"{{{WP}}}anchor"):
        ext = anchor.find(f"{{{WP}}}extent")
        cx = int(ext.get("cx", 0)) if ext is not None else 0
        cy = int(ext.get("cy", 0)) if ext is not None else 0
        print(f"  {label} anchor: {cx/EMU:.2f}x{cy/EMU:.2f} cm")


body = root.find(wtag("body"))
project_tables = []
for i, el in enumerate(list(body)):
    if el.tag != wtag("tbl"):
        continue
    rows = el.findall(wtag("tr"))
    first = ""
    for tr in rows:
        for tc in tr.findall(wtag("tc")):
            t = "".join((x.text or "") + (x.tail or "") for x in tc.iter(wtag("t"))).strip()
            if t:
                first = t[:50]
                break
        if first:
            break
    if first.startswith("Project:") or "A22102" in first:
        project_tables.append((i, el, first[:40]))

for bi, tbl, label in project_tables:
    print(f"\n=== body[{bi}] {label} ===")
    rows = tbl.findall(wtag("tr"))
    for ri, tr in enumerate(rows):
        has_img = False
        for ci, tc in enumerate(tr.findall(wtag("tc"))):
            before = has_img
            find_images_in_element(tc, f"r{ri}c{ci}")
            # check paragraphs for drawings
            for pi, p in enumerate(tc.findall(wtag("p"))):
                if list(p.iter(f"{{{WP}}}inline")) or list(p.iter(f"{{{WP}}}anchor")):
                    has_img = True
        if ri <= 2:
            tr_pr = tr.find(wtag("trPr"))
            if tr_pr is not None:
                th = tr_pr.find(wtag("trHeight"))
                if th is not None:
                    print(f"  r{ri} trHeight val={th.get(wtag('val'))} rule={th.get(wtag('rule'))}")

# paragraphs BETWEEN tables with images
all_body = list(body)
for bi, tbl, label in project_tables:
    # find paras between this table and previous
    tbl_idx = all_body.index(tbl)
    # paras before table in body? - actually paras are separate body elements
    pass

# Check paras right after each project table
print("\n=== PARAGRAPHS ADJACENT TO PROJECT TABLES ===")
for idx, el in enumerate(all_body):
    if el.tag != wtag("tbl"):
        continue
    txt = "".join((t.text or "") + (t.tail or "") for t in el.iter(wtag("t"))).strip()[:40]
    if not txt.startswith("Project:") and "A22102" not in txt and "B1203" not in txt:
        continue
    print(f"\nTable at body[{idx}]: {txt}")
    # look at next 3 body elements
    for j in range(idx + 1, min(idx + 8, len(all_body))):
        nel = all_body[j]
        tag = nel.tag.split("}")[-1]
        if tag == "p":
            pt = "".join((t.text or "") + (t.tail or "") for t in nel.iter(wtag("t"))).strip()
            imgs = len(list(nel.iter(f"{{{WP}}}inline"))) + len(list(nel.iter(f"{{{WP}}}anchor")))
            print(f"  body[{j}] p imgs={imgs} text={pt[:50]!r}")
        elif tag == "tbl":
            nt = "".join((t.text or "") + (t.tail or "") for t in nel.iter(wtag("t"))).strip()[:40]
            print(f"  body[{j}] tbl start={nt!r}")
            break
