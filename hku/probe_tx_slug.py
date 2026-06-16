# -*- coding: utf-8 -*-
import json
import re
import urllib.request

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
urls = {
    "吉喆": "https://www.midland.com.hk/zh-hk/new-property/%E6%B8%AF%E5%B3%B6-%E5%A0%85%E5%B0%BC%E5%9C%B0%E5%9F%8E-%E5%90%89%E5%96%86-E000019385",
    "Eight South Lane": "https://www.midland.com.hk/zh-hk/estate/%E6%B8%AF%E5%B3%B6-%E5%A0%85%E5%B0%BC%E5%9C%B0%E5%9F%8E-Eight-South-Lane-E000015221",
    "翰林峰": "https://www.midland.com.hk/zh-hk/estate/%E6%B8%AF%E5%B3%B6-%E8%A5%BF%E7%87%9F%E7%9B%A4-%E7%BF%B0%E6%9E%97%E5%B3%B0-E000015984",
}

for name, url in urls.items():
    est_id = re.search(r"(E\d{9})", url).group(1)
    html = urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=30).read().decode()
    links = set(re.findall(r'/zh-hk/list/transaction/[^"\']+', html))
    own = [l for l in links if est_id in l]
    print(name, est_id, own[:2])
