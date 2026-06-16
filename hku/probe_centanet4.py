# -*- coding: utf-8 -*-
import json
import re
import urllib.request
from pathlib import Path

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
url = "https://hk.centanet.com/findproperty/zh-cn/list/transaction/%E7%BF%B0%E6%9E%97%E5%B3%B0_2-SSPPWWPOWG"
html = urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=30).read().decode("utf-8", "replace")

# extract transaction objects from embedded payload
items = []
for m in re.finditer(
    r'\{id:"([A-Z]{3}\d{6}R\d+)"[^}]{0,2000}?transactionPrice:(\d+)[^}]{0,500}?\}',
    html,
):
    blob = m.group(0)
    tid = m.group(1)
    price = int(m.group(2))
    addr_m = re.search(r'line1:"([^"]+)"', blob)
    date_m = re.search(r'transDate[^:]*:"([^"]+)"', blob) or re.search(r'"(\d{8})"', tid)
    area_m = re.search(r'area:\{[^}]*?value:(\d+)', blob) or re.search(r'netArea:(\d+)', blob)
    age_m = re.search(r'opYear:(\d+)', blob)
    type_m = re.search(r'unitType:\{[^}]*?value:"([^"]+)"', blob)
    items.append(
        {
            "id": tid,
            "price": price,
            "addr": addr_m.group(1) if addr_m else None,
            "blob_snip": blob[:400],
        }
    )

Path("tx_items.json").write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
print(len(items))

# try detail URL construction
for prefix in [
    "https://hk.centanet.com/findproperty/zh-cn/transaction-detail/%E7%BF%B0%E6%9E%97%E5%B3%B0_",
    "https://hk.centanet.com/findproperty/zh-cn/transaction-detail/-%E7%BF%B0%E6%9E%97%E5%B3%B0_",
]:
    test = prefix + "SYA202605R1174"
    try:
        h = urllib.request.urlopen(urllib.request.Request(test, headers=HEADERS), timeout=20).read().decode()[:500]
        ok = "成交日期" in h or "出租" in h
        print(test, ok)
    except Exception as e:
        print(test, e)
