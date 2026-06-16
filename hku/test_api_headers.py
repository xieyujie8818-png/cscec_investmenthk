# -*- coding: utf-8 -*-
import json
import urllib.request

BASE = "https://data.midland.com.hk/search/v2/transactions"
params = "q=c284856f&ad=true&chart=true&lang=zh-hk&currency=HKD&unit=feet&search_behavior=normal&tx_date=3year&limit=24"
url = f"{BASE}?{params}"

header_sets = [
    {"User-Agent": "Mozilla/5.0", "Referer": "https://www.midland.com.hk/"},
    {"User-Agent": "Mozilla/5.0", "Referer": "https://www.midland.com.hk/zh-hk/list/transaction/%E6%90%9C%E5%B0%8B-H-c284856f", "Origin": "https://www.midland.com.hk"},
    {"User-Agent": "Mozilla/5.0", "Accept": "application/json", "Referer": "https://www.midland.com.hk/", "Origin": "https://www.midland.com.hk", "x-api-key": "midland"},
]

# Direct params without hash
url2 = BASE + "?lang=zh-hk&currency=HKD&unit=feet&search_behavior=normal&tx_type=L&est_ids=E000019385&tx_date=90days&limit=100"

for name, u in [("hash", url), ("direct", url2)]:
    for i, h in enumerate(header_sets):
        try:
            r = urllib.request.urlopen(urllib.request.Request(u, headers=h), timeout=20)
            d = json.loads(r.read())
            print(name, i, "OK", len(d.get("result", [])))
            if d.get("result"):
                print(" ", d["result"][0].get("estate"), d["result"][0].get("price"))
        except Exception as e:
            print(name, i, "ERR", e)

# Try hash lookup
for path in [
    "https://data.midland.com.hk/search/v2/hash/c284856f",
    "https://data.midland.com.hk/search/v2/history/c284856f",
    "https://data.midland.com.hk/member/history/v1/search_histories?q=c284856f&lang=zh-hk&subject=transaction",
]:
    try:
        r = urllib.request.urlopen(urllib.request.Request(path, headers=header_sets[1]), timeout=20)
        print(path, "OK", r.read()[:500])
    except Exception as e:
        print(path, "ERR", e)
