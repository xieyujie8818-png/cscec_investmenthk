import json, re, urllib.request
H = {"User-Agent": "Mozilla/5.0"}
url = "https://www.midland.com.hk/zh-hk/estate/%E6%B8%AF%E5%B3%B6-%E8%A5%BF%E7%87%9F%E7%9B%A4-Kensington-Hill-E000015321"
html = urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=30).read().decode()
for pat in [r"放盤租價\s*\\?\$([\d,]+)\s*-\s*\\?\$([\d,]+)", r"放盤平均呎租\s*\\?\$([\d,]+)", r"min_rent.: (\d+)"]:
    m = re.search(pat, html)
    print(pat[:30], m.groups() if m else None)
