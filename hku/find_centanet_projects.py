# -*- coding: utf-8 -*-
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
PROJECTS = [
    "吉喆",
    "翰林峰",
    "Kennedy 38",
    "嘉林閣",
    "碧瑤灣",
    "豪峰II",
    "美林園",
    "Victoria Coast",
]

out = {}
for name in PROJECTS:
    q = urllib.parse.quote(name)
    search = f"https://hk.centanet.com/findproperty/zh-cn/search?keyword={q}"
    try:
        html = urllib.request.urlopen(
            urllib.request.Request(search, headers=HEADERS), timeout=30
        ).read().decode("utf-8", "replace")
    except Exception as e:
        out[name] = {"error": str(e)}
        continue
    tx_links = re.findall(
        r"/findproperty(?:/zh-cn)?/list/transaction/([^\"'?]+)", html
    )
    estate_links = re.findall(r"/estate/([^\"'?]+)", html)
    out[name] = {"tx": list(dict.fromkeys(tx_links))[:5], "estate": list(dict.fromkeys(estate_links))[:3]}

Path(__file__).parent.joinpath("centanet_project_urls.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
)
print("done")
