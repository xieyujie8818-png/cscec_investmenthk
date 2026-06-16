"""
Fix image proportions and table layout in CWN CV only.
Skips A22102 table entirely. Does not change text content.
"""
import re
import shutil
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

WNS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
WP = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
PIC = "http://schemas.openxmlformats.org/drawingml/2006/picture"

EMU_PER_CM = 360000
GAP_CM = 0.25


def wtag(name):
    return f"{{{WNS}}}{name}"


def wptag(name):
    return f"{{{WP}}}{name}"


def atag(name):
    return f"{{{A}}}{name}"


def cell_text(tc):
    return "".join((t.text or "") + (t.tail or "") for t in tc.iter(wtag("t"))).strip()


def row_text(tr):
    return " ".join(cell_text(tc) for tc in tr.findall(wtag("tc"))).strip()


def table_text(tbl):
    return "".join((t.text or "") + (t.tail or "") for t in tbl.iter(wtag("t")))


def is_a22102_table(tbl):
    return "A22102" in table_text(tbl)


def is_project_table(tbl):
    if tbl.tag != wtag("tbl"):
        return False
    t = table_text(tbl)
    return t.startswith("Project:") or ("Project:" in t[:120] and "Staff assigned" not in t)


def para_has_anchor(p):
    return bool(list(p.iter(wptag("anchor"))) or list(p.iter(wptag("inline"))))


def row_has_anchor(tr):
    return bool(list(tr.iter(wptag("anchor"))) or list(tr.iter(wptag("inline"))))


def get_anchors_in_row(tr):
    items = []
    for ci, tc in enumerate(tr.findall(wtag("tc"))):
        for pi, p in enumerate(tc.findall(wtag("p"))):
            for a in p.iter(wptag("anchor")):
                items.append((ci, pi, p, a))
            for a in p.iter(wptag("inline")):
                items.append((ci, pi, p, a))
    return items


def set_extents(anchor, cx, cy):
    ext = anchor.find(wptag("extent"))
    if ext is not None:
        ext.set("cx", str(int(cx)))
        ext.set("cy", str(int(cy)))
    for ext2 in anchor.iter(atag("ext")):
        ext2.set("cx", str(int(cx)))
        ext2.set("cy", str(int(cy)))


def get_extents(anchor):
    ext = anchor.find(wptag("extent"))
    if ext is not None:
        return int(ext.get("cx", 0)), int(ext.get("cy", 0))
    return 0, 0


def set_horizontal_offset(anchor, offset_emu):
    pos_h = anchor.find(wptag("positionH"))
    if pos_h is None:
        pos_h = ET.SubElement(anchor, wptag("positionH"))
        pos_h.set("relativeFrom", "column")
    pos_offset = pos_h.find(wptag("posOffset"))
    if pos_offset is None:
        pos_offset = ET.SubElement(pos_h, wptag("posOffset"))
    pos_offset.text = str(int(offset_emu))


def set_vertical_offset(anchor, offset_emu):
    pos_v = anchor.find(wptag("positionV"))
    if pos_v is None:
        pos_v = ET.SubElement(anchor, wptag("positionV"))
        pos_v.set("relativeFrom", "paragraph")
    pos_offset = pos_v.find(wptag("posOffset"))
    if pos_offset is None:
        pos_offset = ET.SubElement(pos_v, wptag("posOffset"))
    pos_offset.text = str(int(offset_emu))


def resize_preserve_ratio(anchor, target_width_emu, max_height_emu=None):
    cx, cy = get_extents(anchor)
    if cx <= 0 or cy <= 0:
        return target_width_emu, target_width_emu
    ratio = cy / cx
    new_cx = target_width_emu
    new_cy = int(new_cx * ratio)
    if max_height_emu and new_cy > max_height_emu:
        new_cy = max_height_emu
        new_cx = int(new_cy / ratio)
    set_extents(anchor, new_cx, new_cy)
    return new_cx, new_cy


def trim_empty_paragraphs_in_cell(tc, keep_with_anchors=True):
    paras = tc.findall(wtag("p"))
    if not paras:
        return 0
    removed = 0
    # Keep one empty paragraph if cell would become empty
    anchor_paras = [p for p in paras if para_has_anchor(p)]
    non_empty = [p for p in paras if not para_has_anchor(p) and "".join(
        (t.text or "") + (t.tail or "") for t in p.iter(wtag("t"))
    ).strip()]
    to_remove = []
    for p in paras:
        if para_has_anchor(p):
            continue
        if p in non_empty:
            continue
        to_remove.append(p)
    # leave at least one p in cell
    remaining = len(paras) - len(to_remove)
    if remaining < 1:
        to_remove = to_remove[:-1] if to_remove else []
    for p in to_remove:
        tc.remove(p)
        removed += 1
    return removed


def remove_empty_spacer_rows(tbl):
    removed = 0
    for tr in list(tbl.findall(wtag("tr"))):
        if row_has_anchor(tr):
            continue
        if row_text(tr):
            continue
        # empty row with only empty cells
        tbl.remove(tr)
        removed += 1
    return removed


def clear_row_height(tr):
    tr_pr = tr.find(wtag("trPr"))
    if tr_pr is None:
        return
    th = tr_pr.find(wtag("trHeight"))
    if th is not None:
        tr_pr.remove(th)


def set_row_height(tr, height_emu):
    tr_pr = tr.find(wtag("trPr"))
    if tr_pr is None:
        tr_pr = ET.SubElement(tr, wtag("trPr"))
    th = tr_pr.find(wtag("trHeight"))
    if th is None:
        th = ET.SubElement(tr_pr, wtag("trHeight"))
    th.set(wtag("val"), str(int(height_emu)))
    th.set(wtag("hRule"), "atLeast")


def layout_images_in_row(tr):
    anchors = [a for _, _, _, a in get_anchors_in_row(tr)]
    if not anchors:
        return None

    n = len(anchors)
    max_h_emu = int(4.6 * EMU_PER_CM)

    if n == 1:
        w_emu = int(5.8 * EMU_PER_CM)
        cx, cy = resize_preserve_ratio(anchors[0], w_emu, max_h_emu)
        set_horizontal_offset(anchors[0], 0)
        set_vertical_offset(anchors[0], int(0.08 * EMU_PER_CM))
        return cy + int(0.2 * EMU_PER_CM)

    if n == 2:
        gap = int(GAP_CM * EMU_PER_CM)
        w_emu = int(4.9 * EMU_PER_CM)
        ratios = []
        for a in anchors:
            cx, cy = get_extents(a)
            ratios.append((cy / cx) if cx else 1.0)
        max_cy_at_w = max(int(w_emu * r) for r in ratios)
        if max_cy_at_w > max_h_emu:
            w_emu = int(max_h_emu / max(ratios))
        max_cy = 0
        for i, (a, ratio) in enumerate(zip(anchors, ratios)):
            new_cy = int(w_emu * ratio)
            set_extents(a, w_emu, new_cy)
            set_horizontal_offset(a, i * (w_emu + gap))
            set_vertical_offset(a, int(0.08 * EMU_PER_CM))
            max_cy = max(max_cy, new_cy)
        return max_cy + int(0.2 * EMU_PER_CM)

    # 3+ images: equal width tiles
    w_emu = int(3.7 * EMU_PER_CM)
    gap = int(GAP_CM * EMU_PER_CM)
    max_cy = 0
    for i, a in enumerate(anchors):
        cx, cy = resize_preserve_ratio(a, w_emu, max_h_emu)
        set_horizontal_offset(a, i * (w_emu + gap))
        set_vertical_offset(a, int(0.08 * EMU_PER_CM))
        max_cy = max(max_cy, cy)
    return max_cy + int(0.2 * EMU_PER_CM)


def fix_project_table(tbl):
    if is_a22102_table(tbl):
        return {"skipped": True}

    stats = {
        "skipped": False,
        "rows_removed": 0,
        "paras_removed": 0,
        "images_layout": 0,
    }

    stats["rows_removed"] += remove_empty_spacer_rows(tbl)

    rows = tbl.findall(wtag("tr"))
    for tr in rows:
        if row_has_anchor(tr):
            clear_row_height(tr)
            needed_h = layout_images_in_row(tr)
            if needed_h:
                set_row_height(tr, needed_h)
                stats["images_layout"] += 1
        else:
            clear_row_height(tr)

        for tc in tr.findall(wtag("tc")):
            stats["paras_removed"] += trim_empty_paragraphs_in_cell(tc)

    return stats


def remove_gap_paragraphs_between_projects(body):
    children = list(body)
    project_idxs = [
        i
        for i, el in enumerate(children)
        if el.tag == wtag("tbl") and is_project_table(el) and not is_a22102_table(el)
    ]
    removed = 0
    for a, b in zip(project_idxs, project_idxs[1:]):
        for el in list(children[a + 1 : b]):
            if el.tag != wtag("p"):
                continue
            txt = "".join((t.text or "") + (t.tail or "") for t in el.iter(wtag("t"))).strip()
            if not txt and not para_has_anchor(el):
                body.remove(el)
                removed += 1
    return removed


def remove_large_empty_para_gaps_in_section(body):
    """Remove long runs of empty paragraphs in 1.2.1 project section only."""
    children = list(body)
    removed = 0
    in_section = False
    i = 0
    while i < len(children):
        el = children[i]
        if el.tag == wtag("p"):
            txt = "".join((t.text or "") + (t.tail or "") for t in el.iter(wtag("t"))).strip()
            if "1.2.1" in txt and "Similar" in txt:
                in_section = True
            if "1.2.2" in txt or "Duties and Responsibility" in txt:
                in_section = False
        if in_section and el.tag == wtag("p"):
            txt = "".join((t.text or "") + (t.tail or "") for t in el.iter(wtag("t"))).strip()
            if not txt and not para_has_anchor(el):
                # check if inside or between project tables - remove standalone empty p
                body.remove(el)
                children = list(body)
                removed += 1
                continue
        i += 1
    return removed


def apply_fix(cv_path: Path):
    with zipfile.ZipFile(cv_path) as zin:
        xml_bytes = zin.read("word/document.xml")
        other = {n: zin.read(n) for n in zin.namelist() if n != "word/document.xml"}

    root = ET.fromstring(xml_bytes)
    body = root.find(wtag("body"))

    all_stats = []
    for el in body:
        if el.tag == wtag("tbl") and is_project_table(el):
            all_stats.append(fix_project_table(el))

    gap_removed = remove_gap_paragraphs_between_projects(body)
    section_empty = remove_large_empty_para_gaps_in_section(body)

    out_xml = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    temp = cv_path.with_suffix(".layout.tmp.docx")
    with zipfile.ZipFile(cv_path) as zin, zipfile.ZipFile(
        temp, "w", compression=zipfile.ZIP_DEFLATED
    ) as zout:
        for item in zin.infolist():
            data = out_xml if item.filename == "word/document.xml" else zin.read(item.filename)
            zout.writestr(item, data)

    shutil.move(temp, cv_path)
    return all_stats, gap_removed, section_empty


if __name__ == "__main__":
    base = Path(r"C:\Users\yujie.xie\.cursor\cohl-marketing\hku\Technical Submission")
    cv = [p for p in base.glob("2.0 4(ii)(iii) CV of CWN*") if "backup" not in p.name.lower()][0]
    backup = [p for p in base.glob("*backup_layout_20260609*")][0]

    print("Target:", cv.name)
    print("Backup:", backup.name)
    stats, gap, sec = apply_fix(cv)
    print("\nTable fixes:")
    for i, s in enumerate(stats):
        print(f"  table {i}: {s}")
    print(f"Gap paragraphs removed: {gap}")
    print(f"Section empty paragraphs removed: {sec}")

    # verify
    with zipfile.ZipFile(cv) as z:
        ok = "word/document.xml" in z.namelist()
    print("Docx valid:", ok)
