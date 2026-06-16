# -*- coding: utf-8 -*-
import json
import re
import urllib.request
from pathlib import Path

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
url = "https://hk.centanet.com/findproperty/zh-cn/list/transaction/%E7%BF%B0%E6%9E%97%E5%B3%B0_2-SSPPWWPOWG"
html = urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=30).read().decode("utf-8", "replace")

tid = "SYA202605R1174"
idx = html.find(tid)
Path("tid_context.txt").write_text(html[max(0, idx - 300) : idx + 300], encoding="utf-8")

# escaped urls
urls = re.findall(r"transaction-detail[^\"'\\]{0,150}", html)
Path("tx_paths.json").write_text(json.dumps(urls[:20], ensure_ascii=False, indent=2), encoding="utf-8")
print("paths", len(urls))
