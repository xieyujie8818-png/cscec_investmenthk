# -*- coding: utf-8 -*-
import json
import re
import urllib.request

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
url = "https://www.midland.com.hk/zh-hk/estate/%E6%B8%AF%E5%B3%B6-%E8%A5%BF%E7%87%9F%E7%9B%A4-%E7%BF%B0%E6%9E%97%E5%B3%B0-E000015984"
html = urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=30).read().decode()
pp = json.loads(re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL).group(1))["props"]["pageProps"]
tdo = pp.get("transactionDataObj", [])
for block in tdo:
    print("label:", block.get("label"), "total:", block.get("total"))
    raw = block.get("rawData", {})
    print("  rawData keys:", list(raw.keys()) if isinstance(raw, dict) else type(raw))
    results = raw.get("result") if isinstance(raw, dict) else None
    if results:
        print("  result count:", len(results))
        for tx in results[:5]:
            print("   ", tx.get("tx_type"), tx.get("tx_date"), tx.get("bedroom"), tx.get("net_area"), tx.get("price"), tx.get("unit_price_net"))

# Search full HTML for rent transactions with tx_type L
for pat in [r'"tx_type":"L"', r'"tx_type":\s*"L"', r'tx_type.: .L.']:
    print(pat, len(re.findall(pat, html)))

# Find transaction API URL in page
for m in re.finditer(r"transactions\?[^\"']+", html):
    s = m.group(0)
    if "tx_type=L" in s or "tx_type%3DL" in s:
        print("API URL snippet:", s[:200])
