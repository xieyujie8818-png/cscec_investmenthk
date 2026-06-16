# -*- coding: utf-8 -*-
import json
import re
import urllib.request

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
url = "https://www.midland.com.hk/zh-hk/estate/%E6%B8%AF%E5%B3%B6-%E8%A5%BF%E7%87%9F%E7%9B%A4-%E7%BF%B0%E6%9E%97%E5%B3%B0-E000015984"
html = urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=30).read().decode("utf-8", "replace")
m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
data = json.loads(m.group(1))
ed = data["props"]["pageProps"]["result"]["estateData"]
print("estateData keys:", list(ed.keys()))
print("name:", ed.get("name"))
print("completion:", ed.get("completion_date") or ed.get("completionDate") or ed.get("date_of_completion"))

# search for rent-related fields
for k, v in ed.items():
    kl = k.lower()
    if any(x in kl for x in ("rent", "listing", "avg", "price", "tran")):
        print(f"\n{k}:", type(v).__name__)
        if isinstance(v, dict):
            print("  keys:", list(v.keys())[:15])
            for sk, sv in v.items():
                if not isinstance(sv, (dict, list)):
                    print(f"    {sk}: {sv}")
        elif isinstance(v, list) and v:
            print("  first:", v[0] if len(str(v[0])) < 300 else str(v[0])[:300])

# transactionDataObj
td = data["props"]["pageProps"].get("transactionDataObj", {})
print("\ntransactionDataObj keys:", list(td.keys()) if isinstance(td, dict) else type(td))
