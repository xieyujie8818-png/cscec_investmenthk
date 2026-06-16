# -*- coding: utf-8 -*-
import json
import openpyxl
from pathlib import Path

p = Path(__file__).parent / "港大周邊私人住宅" / "周邊項目租成交情況.xlsx"
wb = openpyxl.load_workbook(p)
ws = wb.active
out = {"merged": [str(m) for m in ws.merged_cells.ranges], "rows": []}
for r in range(1, 28):
    vals = [ws.cell(r, c).value for c in range(1, 13)]
    if any(v is not None for v in vals):
        out["rows"].append({"r": r, "vals": vals})
Path("xlsx_merged.json").write_text(json.dumps(out, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
