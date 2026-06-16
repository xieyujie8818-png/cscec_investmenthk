# -*- coding: utf-8 -*-
import json
import re
import urllib.request

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# From estate page link pattern
urls = [
    "https://data.midland.com.hk/search/v2/transactions?hash=true&lang=zh-hk&tx_type=L&est_ids=E000015984&limit=50&tx_date=3month",
    "https://data.midland.com.hk/search/v2/transactions?hash=true&lang=zh-hk&tx_type=L&est_ids=E000015984&limit=50&tx_date=90day",
    "https://data.midland.com.hk/search/v2/transactions?hash=true&lang=zh-hk&tx_type=L&est_ids=E000015984&limit=50&tx_date=90d",
]

for url in urls:
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        resp = urllib.request.urlopen(req, timeout=30)
        print(url.split("tx_date=")[1], "status", resp.status)
        data = json.loads(resp.read())
        print("keys", list(data.keys()) if isinstance(data, dict) else type(data))
        results = data.get("result") or data.get("results") or data.get("data") or []
        print("count", len(results))
        if results:
            print(json.dumps(results[0], ensure_ascii=False, indent=2)[:800])
    except Exception as e:
        print(url.split("tx_date=")[1], "ERR", e)

# Also try transaction history page SSR
hist = "https://www.midland.com.hk/zh-hk/transaction-history/%E6%B8%AF%E5%B3%B6-%E8%A5%BF%E7%87%9F%E7%9B%A4-%E7%BF%B0%E6%9E%97%E5%B3%B0-E000015984"
html = urllib.request.urlopen(urllib.request.Request(hist, headers=HEADERS), timeout=30).read().decode()
m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
if m:
    pp = json.loads(m.group(1))["props"]["pageProps"]
    print("\nhistory pageProps keys:", list(pp.keys()))
    for k, v in pp.items():
        if "trans" in k.lower() or "data" in k.lower():
            print(k, type(v).__name__)
