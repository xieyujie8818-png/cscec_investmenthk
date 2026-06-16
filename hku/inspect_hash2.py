# -*- coding: utf-8 -*-
import json
import re
import urllib.request

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
url = "https://www.midland.com.hk/zh-hk/list/transaction/%E6%90%9C%E5%B0%8B-H-c284856f"
html = urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=45).read().decode("utf-8", "replace")

# Extract all JSON blobs containing c284856f
for m in re.finditer(r'\{[^{}]*c284856f[^{}]*\}', html):
    s = m.group(0)
    if len(s) < 500:
        print(s[:400])
        print("---")

# Search for filter/search state near hash
for m in re.finditer(r'.{0,200}c284856f.{0,400}', html):
    chunk = m.group(0)
    if "tx_type" in chunk or "est_ids" in chunk or "bedroom" in chunk or "filter" in chunk:
        print("FILTER CHUNK:", chunk[:600])
        print("---")

# Try data.midland with hash=true redirect pattern from estate pages
urls = [
    "https://data.midland.com.hk/search/v2/transactions?hash=true&redirect=true&lang=zh-hk&hash=c284856f",
    "https://data.midland.com.hk/search/v2/hash/c284856f?lang=zh-hk",
    "https://data.midland.com.hk/search/v2/transactions/c284856f?lang=zh-hk",
]
for u in urls:
    try:
        req = urllib.request.Request(u, headers={**HEADERS, "Referer": url})
        resp = urllib.request.urlopen(req, timeout=20)
        print(u, "OK", len(resp.read()))
    except Exception as e:
        print(u, e)
