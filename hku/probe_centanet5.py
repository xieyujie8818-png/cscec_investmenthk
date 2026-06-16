# -*- coding: utf-8 -*-
import re
import urllib.request
from pathlib import Path

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
url = "https://hk.centanet.com/findproperty/zh-cn/list/transaction/%E7%BF%B0%E6%9E%97%E5%B3%B0_2-SSPPWWPOWG"
html = urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=30).read().decode("utf-8", "replace")

idx = html.find("SYA202605R1174")
Path("blob2.txt").write_text(html[idx : idx + 2500], encoding="utf-8")

# find href patterns with encoded urls
for pat in [r'\\u002Ftransaction-detail\\u002F[^"\\]+', r'/transaction-detail/[^"\\]+']:
    ms = re.findall(pat, html)
    Path(f"paths_{pat[:10]}.txt").write_text("\n".join(ms[:30]), encoding="utf-8")
    print(pat, len(ms))
