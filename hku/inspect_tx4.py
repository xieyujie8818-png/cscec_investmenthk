# -*- coding: utf-8 -*-
import json
import re
import urllib.request

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
url = "https://www.midland.com.hk/zh-hk/estate/%E6%B8%AF%E5%B3%B6-%E8%A5%BF%E7%87%9F%E7%9B%A4-%E7%BF%B0%E6%9E%97%E5%B3%B0-E000015984"
html = urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=30).read().decode()
pp = json.loads(re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL).group(1))["props"]["pageProps"]
print("token:", pp.get("token", "")[:50] if pp.get("token") else None)
tdo = pp.get("transactionDataObj", [])
for block in tdo:
    if block.get("label") == "L":
        print("moreHref:", block.get("moreHref"))
        print("filter:", json.dumps(block.get("rawData", {}).get("filter"), ensure_ascii=False)[:500])

# Try list transaction page for estate rent
list_url = "https://www.midland.com.hk/zh-hk/list/transaction/%E7%BF%B0%E6%9E%97%E5%B3%B0-E-E000015984?tx_type=L"
html2 = urllib.request.urlopen(urllib.request.Request(list_url, headers=HEADERS), timeout=30).read().decode()
m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html2, re.DOTALL)
if m:
    pp2 = json.loads(m.group(1))["props"]["pageProps"]
    print("\nlist tx page keys:", list(pp2.keys()))
    for k in pp2:
        if "trans" in k.lower() or "listing" in k.lower() or "data" in k.lower():
            v = pp2[k]
            if isinstance(v, (dict, list)):
                print(k, type(v).__name__, str(v)[:200] if not isinstance(v, list) else len(v))
