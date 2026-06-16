import json, re, urllib.request, pprint
H = {"User-Agent": "Mozilla/5.0"}
url = "https://www.midland.com.hk/zh-hk/estate/%E6%B8%AF%E5%B3%B6-%E8%A5%BF%E7%87%9F%E7%9B%A4-Kensington-Hill-E000015321"
html = urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=30).read().decode()
ed = json.loads(re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL).group(1))["props"]["pageProps"]["result"]["estateData"]
pprint.pp(ed.get("property_stat"))
