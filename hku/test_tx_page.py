# -*- coding: utf-8 -*-
import json
import re
import urllib.parse
import urllib.request

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

pages = [
    "https://www.midland.com.hk/zh-hk/list/transaction/E-E000019385?tx_type=L&bedroom=0&tx_date=90days",
    "https://www.midland.com.hk/zh-hk/list/transaction/%E5%90%89%E5%96%86-E-E000019385?tx_type=L&bedroom=0&tx_date=90days",
]

apis = [
    "https://data.midland.com.hk/search/v2/transactions?hash=true&redirect=true&lang=zh-hk&currency=HKD&unit=feet&search_behavior=normal&tx_type=L&est_ids=E000019385&bedroom=0&tx_date=90days&limit=100",
]

for url in pages:
    html = urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=30).read().decode()
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
    if not m:
        print(url, "no next data")
        continue
    pp = json.loads(m.group(1))["props"]["pageProps"]
    lds = pp.get("listingDataForSSR") or {}
    results = lds.get("result") or lds.get("results") or []
    print(url[:80], "results", len(results))
    if results:
        print(" ", results[0].get("estate"), results[0].get("price"), results[0].get("bedroom"))

for url in apis:
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers={**HEADERS, "Referer": "https://www.midland.com.hk/"}), timeout=30)
        d = json.loads(r.read())
        print("api", len(d.get("result", [])), d.get("result", [{}])[0].get("price") if d.get("result") else "")
    except Exception as e:
        print("api ERR", e)
