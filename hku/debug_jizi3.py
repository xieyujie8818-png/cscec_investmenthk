# -*- coding: utf-8 -*-
import json, re, urllib.request
H = {"User-Agent": "Mozilla/5.0"}
url = "https://www.midland.com.hk/zh-hk/new-property/%E6%B8%AF%E5%B3%B6-%E5%A0%85%E5%B0%BC%E5%9C%B0%E5%9F%8E-%E5%90%89%E5%96%86-E000019385"
pp = json.loads(re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=30).read().decode(), re.DOTALL).group(1))["props"]["pageProps"]
for k in pp:
    if "transaction" in k.lower() or "rent" in k.lower():
        v = pp[k]
        print(k, type(v).__name__)
        if isinstance(v, list) and v:
            print(json.dumps(v[:3], ensure_ascii=False)[:1500])
        elif isinstance(v, dict):
            print(list(v.keys())[:15])
