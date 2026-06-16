# -*- coding: utf-8 -*-
import json
import re
import urllib.request

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
url = "https://www.midland.com.hk/zh-hk/new-property/%E6%B8%AF%E5%B3%B6-%E5%A0%85%E5%B0%BC%E5%9C%B0%E5%9F%8E-%E5%90%89%E5%96%86-E000019385"
html = urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=30).read().decode("utf-8", "replace")
pp = json.loads(re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL).group(1))["props"]["pageProps"]
npd = pp.get("newPropertyDetail", {})
print("newPropertyDetail keys:", list(npd.keys())[:25])
for k in ["name", "first_op_date", "min_net_area", "max_net_area", "property_stat", "op_date"]:
    print(k, npd.get(k))
# dump property_stat if nested
def find_key(obj, target, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == target:
                print(f"FOUND {path}.{k}:", str(v)[:500])
            find_key(v, target, f"{path}.{k}")
    elif isinstance(obj, list) and obj:
        find_key(obj[0], target, path + "[0]")

find_key(npd, "property_stat")
find_key(npd, "min_rent")
