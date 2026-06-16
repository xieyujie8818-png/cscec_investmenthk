# -*- coding: utf-8 -*-
import json, re, urllib.request
HEADERS = {"User-Agent": "Mozilla/5.0"}
URLS = [
    ("尚譽", "https://www.midland.com.hk/zh-hk/estate/%E6%B8%AF%E5%B3%B6-%E8%A5%BF%E7%87%9F%E7%9B%A4-The-Bonham-E000016618"),
    ("尚譽2", "https://www.midland.com.hk/zh-hk/estate/%E6%B8%AF%E5%B3%B6-%E8%A5%BF%E7%87%9F%E7%9B%A4-%E5%B0%9A%E8%AD%BD-E000016618"),
    ("藝里坊2", "https://www.midland.com.hk/zh-hk/estate/%E6%B8%AF%E5%B3%B6-%E8%A5%BF%E7%87%9F%E7%9B%A4-%E8%97%9D%E9%87%8C%E5%9D%8A%EF%BC%8E2%E8%99%9F-E000016618"),
    ("藝里坊2b", "https://www.midland.com.hk/zh-hk/estate/%E6%B8%AF%E5%B3%B6-%E8%A5%BF%E7%87%9F%E7%9B%A4-%E8%97%9D%E9%87%8C%E5%9D%8A-2%E8%99%9F-E000016618"),
    ("63P", "https://www.midland.com.hk/zh-hk/estate/%E6%B8%AF%E5%B3%B6-%E6%B8%AF%E5%B3%B6%E8%A5%BF-63-Pokfulam-E000016034"),
]
for name, url in URLS:
    try:
        html = urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=20).read().decode('utf-8','replace')
        if '屋苑搜尋' in html and '共找到' in html:
            print(name, 'SEARCH PAGE')
            continue
        data = json.loads(re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL).group(1))
        ed = data['props']['pageProps'].get('result', {}).get('estateData', {})
        print(name, ed.get('name'), extract_year:=ed.get('first_op_date'), (ed.get('property_stat') or {}).get('min_rent'))
    except Exception as e:
        print(name, 'ERR', e)
