# -*- coding: utf-8 -*-
import json
import re
import urllib.request

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
url = "https://www.midland.com.hk/zh-hk/estate/%E6%B8%AF%E5%B3%B6-%E8%A5%BF%E7%87%9F%E7%9B%A4-%E7%BF%B0%E6%9E%97%E5%B3%B0-E000015984"
html = urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=30).read().decode("utf-8", "replace")
ed = json.loads(re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL).group(1))["props"]["pageProps"]["result"]["estateData"]

print("min_net_area", ed.get("min_net_area"), "max_net_area", ed.get("max_net_area"))
print("first_op_date", ed.get("first_op_date"), "last_op_date", ed.get("last_op_date"), "op_date", ed.get("op_date"))

fps = ed.get("floorplans", [])
print("floorplans count", len(fps))
if fps:
    print(json.dumps(fps[0], ensure_ascii=False, indent=2)[:1500])

# rent listings SSR
rent_url = "https://www.midland.com.hk/zh-hk/list/rent/%E7%BF%B0%E6%9E%97%E5%B3%B0-E-E000015984"
html2 = urllib.request.urlopen(urllib.request.Request(rent_url, headers=HEADERS), timeout=30).read().decode("utf-8", "replace")
props2 = json.loads(re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html2, re.DOTALL).group(1))["props"]["pageProps"]
ld = props2.get("listingDataForSSR", {})
print("\nlistingDataForSSR keys:", list(ld.keys()) if isinstance(ld, dict) else type(ld))
if isinstance(ld, dict):
    items = ld.get("results") or ld.get("items") or ld.get("data") or ld.get("listings")
    if isinstance(ld.get("properties"), dict):
        items = ld["properties"].get("results") or ld["properties"].get("items")
    print("items count", len(items) if items else 0)
    if items:
        for it in items[:5]:
            print({k: it.get(k) for k in ["bedroom", "net_area", "rent", "price", "net_ft_rent", "net_ft_price"] if k in it})
