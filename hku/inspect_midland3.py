# -*- coding: utf-8 -*-
import json
import re
import urllib.request

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
url = "https://www.midland.com.hk/zh-hk/estate/%E6%B8%AF%E5%B3%B6-%E8%A5%BF%E7%87%9F%E7%9B%A4-%E7%BF%B0%E6%9E%97%E5%B3%B0-E000015984"
html = urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=30).read().decode("utf-8", "replace")
m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
ed = json.loads(m.group(1))["props"]["pageProps"]["result"]["estateData"]

for key in ["market_stat", "market_stat_by_room", "geo_transaction", "property_stat", "room_keys"]:
    print(f"\n=== {key} ===")
    print(json.dumps(ed.get(key), ensure_ascii=False, indent=2)[:3000])

# Also fetch rent listing page
rent_url = "https://www.midland.com.hk/zh-hk/list/rent/%E7%BF%B0%E6%9E%97%E5%B3%B0-E-E000015984"
html2 = urllib.request.urlopen(urllib.request.Request(rent_url, headers=HEADERS), timeout=30).read().decode("utf-8", "replace")
m2 = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html2, re.DOTALL)
props2 = json.loads(m2.group(1))["props"]["pageProps"]
print("\n=== rent list pageProps keys ===", list(props2.keys()))
result = props2.get("result", {})
if isinstance(result, dict):
    print("result keys:", list(result.keys())[:20])
    listings = result.get("listings") or result.get("properties") or result.get("data")
    if listings:
        print("listings type", type(listings))
        if isinstance(listings, dict):
            print("listings keys", list(listings.keys()))
            items = listings.get("items") or listings.get("results") or listings.get("data")
            if items:
                print("first item keys", list(items[0].keys()) if items else None)
                print(json.dumps(items[:3], ensure_ascii=False, indent=2)[:2000])
