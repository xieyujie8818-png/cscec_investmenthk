# -*- coding: utf-8 -*-
import re
import urllib.request

url = "https://hk.centanet.com/findproperty/zh-cn/transaction-detail/-%E7%A2%A7%E7%91%B6%E6%B9%BE_BGV202602R1207"
html = urllib.request.urlopen(
    urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=30
).read().decode("utf-8", "replace")

# dump structured data from HTML
for label in ["成交日期", "出租价", "实用", "建筑", "间隔", "楼龄", "座向", "已租", "已售"]:
    if label in html:
        i = html.find(label)
        print(label, repr(html[i : i + 80]))

# JSON blobs
for m in re.finditer(r'\{[^{}]{50,500}?"rent"[^{}]{0,200}\}', html):
    print("json?", m.group(0)[:200])

# slug in page
paths = re.findall(r"transaction-detail/[^\"']+", html)
print("paths", set(paths))
