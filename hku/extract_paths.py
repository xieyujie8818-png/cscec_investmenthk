# -*- coding: utf-8 -*-
import json
import re
import urllib.request

HEADERS = {"User-Agent": "Mozilla/5.0"}
urls = {
    "豪峰II": "https://hk.centanet.com/findproperty/zh-cn/list/transaction/Royalton-II_2-SDPPWWPJWS",
    "豪峰": "https://hk.centanet.com/findproperty/zh-cn/list/transaction/%E8%B1%AA%E5%B3%B0_2-OJCJURVVRO",
    "美林園": "https://hk.centanet.com/findproperty/zh-cn/list/transaction/%E7%BE%8E%E7%90%B3%E5%9C%92_1-TITNZHTXHT",
    "美琳苑": "https://hk.centanet.com/findproperty/zh-cn/list/transaction/%E7%BE%8E%E7%90%B3%E5%9C%92_1-TITNZHTXHT",
}

def extract_paths(html):
    paths = set()
    for m in re.finditer(r"transaction-detail\\u002F([^\"\\]+)", html):
        paths.add(m.group(1).replace("\\u002F", "/"))
    for m in re.finditer(r"/transaction-detail/([^\"'\\]+)", html):
        paths.add(m.group(1))
  # ids with R only
    rent_paths = [p for p in paths if re.search(r"[A-Z]{3}\d{6}R\d+", p)]
    return sorted(rent_paths)

out = {}
for name, url in urls.items():
    html = urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=30).read().decode("utf-8", "replace")
    out[name] = extract_paths(html)[:10]

open("extract_paths.json", "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=2))
