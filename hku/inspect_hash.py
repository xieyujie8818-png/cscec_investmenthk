# -*- coding: utf-8 -*-
import json
import re
import urllib.request

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
url = "https://www.midland.com.hk/zh-hk/list/transaction/%E6%90%9C%E5%B0%8B-H-c284856f"
html = urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=45).read().decode("utf-8", "replace")

# Find hash references and API URLs
for pat in [r"c284856f", r"search/v2/transactions[^\"']*", r"hash[^\"']{0,80}c284856f", r"tx_type", r"90", r"3month"]:
    matches = re.findall(pat, html)
    if matches:
        print(pat, "count", len(matches), "sample", matches[:3])

# Look for encoded search state in page
idx = html.find("c284856f")
if idx >= 0:
    print("\ncontext:", html[max(0, idx-300):idx+500])

# Try hash decode API endpoints
for api in [
    "https://data.midland.com.hk/search/v2/transactions?hash=c284856f&lang=zh-hk",
    "https://data.midland.com.hk/search/v2/transactions?hash=true&redirect=true&hash_id=c284856f&lang=zh-hk",
    "https://www.midland.com.hk/api/search/hash/c284856f",
]:
    try:
        r = urllib.request.urlopen(urllib.request.Request(api, headers=HEADERS), timeout=20)
        body = r.read()[:2000]
        print(f"\n{api}\n  status {r.status} body {body[:500]}")
    except Exception as e:
        print(f"\n{api}\n  ERR {e}")
