# -*- coding: utf-8 -*-
import json
import re
import urllib.parse
import urllib.request

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
url = "https://www.midland.com.hk/zh-hk/estate/%E6%B8%AF%E5%B3%B6-%E8%A5%BF%E7%87%9F%E7%9B%A4-%E7%BF%B0%E6%9E%97%E5%B3%B0-E000015984"
html = urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=30).read().decode()
pp = json.loads(re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL).group(1))["props"]["pageProps"]
token = pp.get("token")
est_id = "E000015984"

params = {
    "lang": "zh-hk",
    "currency": "HKD",
    "unit": "feet",
    "est_ids": est_id,
    "tx_type": "L",
    "bedroom": "all",
    "page": 1,
    "limit": 100,
    "tx_date": "3month",
}
api = "https://data.midland.com.hk/search/v2/transactions?" + urllib.parse.urlencode(params)
for auth in [None, f"Bearer {token}"]:
    h = dict(HEADERS)
    if auth:
        h["Authorization"] = auth
    try:
        resp = urllib.request.urlopen(urllib.request.Request(api, headers=h), timeout=30)
        data = json.loads(resp.read())
        print("auth", bool(auth), "count", len(data.get("result", [])))
    except Exception as e:
        print("auth", bool(auth), "ERR", e)

# Try internal API path from page
for m in re.finditer(r"https://data\.midland\.com\.hk[^\"']+", html):
    u = m.group(0).replace("\\u0026", "&")
    if "tx_type=L" in u or "tx_type%3DL" in u:
        print("found", u[:250])
