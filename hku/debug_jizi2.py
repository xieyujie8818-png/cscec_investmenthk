# -*- coding: utf-8 -*-
import json
import re
import urllib.request

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
url = "https://www.midland.com.hk/zh-hk/new-property/%E6%B8%AF%E5%B3%B6-%E5%A0%85%E5%B0%BC%E5%9C%B0%E5%9F%8E-%E5%90%89%E5%96%86-E000019385"
html = urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=30).read().decode("utf-8", "replace")
pp = json.loads(re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL).group(1))["props"]["pageProps"]
npd = pp.get("newPropertyDetail", {})
print(json.dumps(npd.get("geo_transaction"), ensure_ascii=False, indent=2)[:2000])
# search entire pageProps for min_rent
text = json.dumps(pp)
for kw in ["min_rent", "avg_net_ft_rent", "property_stat", "rooms"]:
    idx = text.find(kw)
    if idx >= 0:
        print(f"\n{kw}:", text[idx:idx+400])
