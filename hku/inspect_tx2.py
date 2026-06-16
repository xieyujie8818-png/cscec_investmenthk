# -*- coding: utf-8 -*-
import json
import re
import urllib.request
from datetime import datetime, timedelta

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
cutoff = datetime.now() - timedelta(days=90)

def parse_date(s):
    if not s:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%S.000Z", "%d/%m/%y", "%d/%m/%Y"):
        try:
            return datetime.strptime(s[:19] if "T" in s else s, fmt.replace(".%f", "") if "T" not in s else fmt)
        except ValueError:
            continue
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return None

# Estate page transactionDataObj
url = "https://www.midland.com.hk/zh-hk/estate/%E6%B8%AF%E5%B3%B6-%E8%A5%BF%E7%87%9F%E7%9B%A4-%E7%BF%B0%E6%9E%97%E5%B3%B0-E000015984"
html = urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=30).read().decode()
pp = json.loads(re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL).group(1))["props"]["pageProps"]
tdo = pp.get("transactionDataObj")
print("transactionDataObj type", type(tdo), "len", len(tdo) if isinstance(tdo, list) else "")
if isinstance(tdo, list) and tdo:
    print("first keys", list(tdo[0].keys()) if isinstance(tdo[0], dict) else tdo[0])

# transaction history page
hist = "https://www.midland.com.hk/zh-hk/transaction-history/%E6%B8%AF%E5%B3%B6-%E8%A5%BF%E7%87%9F%E7%9B%A4-%E7%BF%B0%E6%9E%97%E5%B3%B0-E000015984"
html2 = urllib.request.urlopen(urllib.request.Request(hist, headers=HEADERS), timeout=30).read().decode()
pp2 = json.loads(re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html2, re.DOTALL).group(1))["props"]["pageProps"]
print("\nhistory keys:", list(pp2.keys()))
for k in pp2:
    if "trans" in k.lower() or "Trans" in k:
        v = pp2[k]
        print(k, type(v).__name__)
        if isinstance(v, dict):
            print("  subkeys", list(v.keys())[:15])
            for sk in ("result", "transactions", "data", "rent", "sell"):
                if sk in v:
                    r = v[sk]
                    print(f"  {sk} len", len(r) if isinstance(r, list) else type(r))
                    if isinstance(r, list) and r:
                        print(json.dumps(r[0], ensure_ascii=False)[:500])

# geo_transaction rent from estate
ed = pp.get("result", {}).get("estateData", {})
rents = ed.get("geo_transaction", {}).get("secondhand_rent", [])
print("\ngeo secondhand_rent count", len(rents))
print(json.dumps(rents[:3], ensure_ascii=False, indent=2))
