# -*- coding: utf-8 -*-
import json
import re
import urllib.request

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

URLS = [
    ("吉喆", "https://www.midland.com.hk/zh-hk/new-property/%E6%B8%AF%E5%B3%B6-%E5%A0%85%E5%B0%BC%E5%9C%B0%E5%9F%8E-%E5%90%89%E5%96%86-E000019385"),
    ("Eight South Lane", "https://www.midland.com.hk/zh-hk/estate/%E6%B8%AF%E5%B3%B6-%E8%A5%BF%E7%87%9F%E7%9B%A4-Eight-South-Lane-E000015985"),
    ("高士台", "https://www.midland.com.hk/zh-hk/estate/%E6%B8%AF%E5%B3%B6-%E8%A5%BF%E7%87%9F%E7%9B%A4-%E9%AB%98%E5%A3%AB%E5%8F%B0-E000014812"),
    ("63 Pokfulam", "https://www.midland.com.hk/zh-hk/estate/%E6%B8%AF%E5%B3%B6-%E8%A5%BF%E7%87%9F%E7%9B%A4-63-Pokfulam-E000015983"),
    ("藝里坊．2號", "https://www.midland.com.hk/zh-hk/estate/%E6%B8%AF%E5%B3%B6-%E8%A5%BF%E7%87%9F%E7%9B%A4-%E8%97%9D%E9%87%8C%E5%9D%8A%EF%BC%8E2%E8%99%9F-E000017131"),
    ("維港峰", "https://www.midland.com.hk/zh-hk/estate/%E6%B8%AF%E5%B3%B6-%E8%A5%BF%E7%87%9F%E7%9B%A4-%E7%B6%AD%E6%B8%AF%E5%B3%B0-E000014811"),
    ("尚譽", "https://www.midland.com.hk/zh-hk/estate/%E6%B8%AF%E5%B3%B6-%E4%B8%AD%E8%A5%BF%E5%8D%80-%E5%B0%9A%E8%AD%BD-E000015986"),
]

for name, url in URLS:
    html = urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=30).read().decode("utf-8", "replace")
    data = json.loads(re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL).group(1))
    pp = data["props"]["pageProps"]
    result = pp.get("result", {})
    print(f"\n=== {name} ===")
    print("result keys:", list(result.keys())[:15] if isinstance(result, dict) else result)
    if isinstance(result, dict):
        for k in result:
            if "data" in k.lower() or "estate" in k.lower() or "property" in k.lower() or "new" in k.lower():
                v = result[k]
                print(f"  {k}: {type(v).__name__}", list(v.keys())[:10] if isinstance(v, dict) else "")
