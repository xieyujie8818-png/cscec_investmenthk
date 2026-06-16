# -*- coding: utf-8 -*-
import json
import re
import urllib.request

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
url = "https://www.midland.com.hk/zh-hk/estate/%E6%B8%AF%E5%B3%B6-%E8%A5%BF%E7%87%9F%E7%9B%A4-%E7%BF%B0%E6%9E%97%E5%B3%B0-E000015984"
html = urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=30).read().decode("utf-8", "replace")
m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
data = json.loads(m.group(1))
props = data.get("props", {}).get("pageProps", {})
print("pageProps keys:", list(props.keys()))

def walk(obj, path="", depth=0, max_depth=4):
    if depth > max_depth:
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{path}.{k}" if path else k
            if k in ("rentListings", "listings", "rent", "transactions", "estateInfo", "estate", "summary", "rentSummary", "listingRent", "rentListing"):
                print("FOUND", p, type(v).__name__, str(v)[:200])
            if isinstance(v, (dict, list)) and depth < max_depth:
                walk(v, p, depth + 1, max_depth)
    elif isinstance(obj, list) and obj:
        walk(obj[0], path + "[0]", depth + 1, max_depth)

walk(props)

# dump estate-related top keys
for k in props:
    if "estate" in k.lower() or "rent" in k.lower() or "listing" in k.lower():
        v = props[k]
        print("KEY", k, type(v).__name__)
        if isinstance(v, dict):
            print("  subkeys:", list(v.keys())[:20])
