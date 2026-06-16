# -*- coding: utf-8 -*-
import json
import re
import urllib.request

url = "https://hk.centanet.com/findproperty/zh-cn/list/transaction/%E7%A2%A7%E7%91%B6%E6%B9%BE_2-OJQCFRCORO?q=udjgk03it5jzb"
html = urllib.request.urlopen(
    urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=30
).read().decode("utf-8", "replace")
print("len", len(html))
for pat in ["__NEXT_DATA__", "transaction-detail", "BGV", "api.", "graphql"]:
    print(pat, html.count(pat))

links = set(re.findall(r"/findproperty/zh-cn/transaction-detail/[^\"'\\]+", html))
print("detail links", len(links), list(links)[:5])
ids = list(dict.fromkeys(re.findall(r"BGV\d{6}R\d+", html)))
print("BGV ids", len(ids), ids[:10])
for pat in [
    r"transaction-detail[^\"']{0,120}",
    r"href[^>]{0,80}BGV202602R1207",
]:
    ms = re.findall(pat, html)
    print(pat, ms[:3])

m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
if m:
    d = json.loads(m.group(1))
    pp = d.get("props", {}).get("pageProps", {})
    print("pageProps keys", list(pp.keys()))

# transaction detail page
detail = "https://hk.centanet.com/findproperty/zh-cn/transaction-detail/-%E7%A2%A7%E7%91%B6%E6%B9%BE_BGV202602R1207"
html2 = urllib.request.urlopen(
    urllib.request.Request(detail, headers={"User-Agent": "Mozilla/5.0"}), timeout=30
).read().decode("utf-8", "replace")
m2 = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html2, re.DOTALL)
if m2:
    pp2 = json.loads(m2.group(1))["props"]["pageProps"]
    print("detail keys", list(pp2.keys()))
    for k, v in pp2.items():
        if isinstance(v, dict) and v:
            print(" ", k, list(v.keys())[:15])
