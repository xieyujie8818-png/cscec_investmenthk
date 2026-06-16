# -*- coding: utf-8 -*-
import json, re, urllib.request
HEADERS = {"User-Agent": "Mozilla/5.0"}
URLS = [
    ("Bonham", "https://www.midland.com.hk/zh-hk/estate/%E6%B8%AF%E5%B3%B6-%E8%A5%BF%E7%87%9F%E7%9B%A4-The-Bonham-E000016135"),
    ("Bonham2", "https://www.midland.com.hk/zh-hk/estate/%E6%B8%AF%E5%B3%B6-%E8%A5%BF%E7%87%9F%E7%9B%A4-%E5%B0%9A%E8%AD%BD-E000016135"),
    ("Art2", "https://www.midland.com.hk/zh-hk/estate/%E6%B8%AF%E5%B3%B6-%E8%A5%BF%E7%87%9F%E7%9B%A4-%E8%97%9D%E9%87%8C%E5%9D%8A%EF%BC%8E2%E8%99%9F-E000017132"),
    ("Art2b", "https://www.midland.com.hk/zh-hk/estate/%E6%B8%AF%E5%B3%B6-%E8%A5%BF%E7%87%9F%E7%9B%A4-%E8%97%9D%E9%87%8C%E5%9D%8A-2%E8%99%9F-E000017132"),
    ("Victoria", "https://www.midland.com.hk/zh-hk/estate/%E6%B8%AF%E5%B3%B6-%E8%A5%BF%E7%87%9F%E7%9B%A4-%E7%B6%AD%E6%B8%AF%E5%B3%B0-E000015322"),
]
for name, url in URLS:
    try:
        html = urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=20).read().decode("utf-8", "replace")
        if "屋苑搜尋" in html and "共找到" in html:
            print(name, "SEARCH PAGE")
            continue
        ed = json.loads(re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL).group(1))["props"]["pageProps"].get("result", {}).get("estateData", {})
        n = ed.get("name", {}).get("chi", "?")
        ps = ed.get("property_stat") or {}
        print(name, n, ed.get("first_op_date"), ps.get("min_rent"), ps.get("max_rent"))
    except Exception as e:
        print(name, "ERR", e)
