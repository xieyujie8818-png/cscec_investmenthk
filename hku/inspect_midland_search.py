# -*- coding: utf-8 -*-
import json
import re
import urllib.request

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
url = "https://www.midland.com.hk/zh-hk/list/transaction/%E6%90%9C%E5%B0%8B-H-c284856f"
html = urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=45).read().decode("utf-8", "replace")
print("len", len(html))
m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
if m:
    pp = json.loads(m.group(1))["props"]["pageProps"]
    print("pageProps keys:", list(pp.keys()))
    for k in pp:
        v = pp[k]
        if isinstance(v, dict) and v:
            print(f"  {k}: dict keys {list(v.keys())[:20]}")
        elif isinstance(v, list) and v:
            print(f"  {k}: list len {len(v)}")
    # listingDataForSSR
    lds = pp.get("listingDataForSSR") or {}
    print("\nlistingDataForSSR keys:", list(lds.keys()) if isinstance(lds, dict) else lds)
    if isinstance(lds, dict):
        for sk in ("results", "items", "data", "transactions", "listings", "properties"):
            if sk in lds:
                r = lds[sk]
                print(f"  {sk}: {type(r).__name__}", len(r) if isinstance(r, list) else list(r.keys())[:10] if isinstance(r, dict) else r)
                if isinstance(r, list) and r:
                    print(json.dumps(r[0], ensure_ascii=False, indent=2)[:1200])
    slug = pp.get("slugObj")
    print("\nslugObj:", json.dumps(slug, ensure_ascii=False)[:800] if slug else None)
    geo = pp.get("geoData")
    print("geoData:", json.dumps(geo, ensure_ascii=False)[:500] if geo else None)
else:
    print("no NEXT_DATA")
    print(html[:2000])
