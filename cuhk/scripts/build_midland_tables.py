# -*- coding: utf-8 -*-
"""Parse Midland estate pages and build Apr/May 2026 summary."""
import re
import urllib.request
from urllib.parse import quote

HEADERS = {"User-Agent": "Mozilla/5.0"}

ESTATES = [
    {
        "name": "大埔寶馬山",
        "url": "https://www.midland.com.hk/zh-hk/estate/%E6%96%B0%E7%95%8C-%E5%A4%A7%E5%9F%94%E5%8D%8A%E5%B1%B1-%E5%A4%A7%E5%9F%94%E5%AF%B6%E9%A6%AC%E5%B1%B1-E11504",
    },
    {
        "name": "天鑽",
        "url": "https://www.midland.com.hk/zh-hk/estate/%E6%96%B0%E7%95%8C-%E5%A4%A7%E5%9F%94%E5%8D%8A%E5%B1%B1-%E5%A4%A9%E9%91%BD-E000016716",
    },
    {
        "name": "逍遙雋岸",
        "url": "https://www.midland.com.hk/zh-hk/estate/%E6%96%B0%E7%95%8C-%E5%A4%A7%E5%9F%94%E5%8D%8A%E5%B1%B1-%E9%80%8D%E9%81%99%E9%9B%8B%E5%B2%B8-E000004058",
    },
]

SEARCH_NAMES = [
    "悠然山莊",
    "雍怡雅苑",
    "翡翠花園",
    "疊翠豪庭",
    "泓山",
    "偉東雍宜山莊",
    "峰林",
    "史提福樓",
    "僑東羅宜山莊",
]


def fetch(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def parse_midland_transactions(html):
    """Extract DD/MM/YY deals with area and psf."""
    deals = []
    # Pattern: 26/04/26...實728呎...@$10,440
    for m in re.finditer(
        r"(\d{2}/\d{2}/26)[^$]{0,200}?實(\d+)呎[^$]{0,80}?@\$([\d,]+)",
        html,
    ):
        date_s, area, psf = m.group(1), int(m.group(2)), int(m.group(3).replace(",", ""))
        if psf < 5000:  # skip rent-like
            continue
        deals.append({"date": date_s, "area": area, "psf": psf, "special": "^" in m.group(0)})
    return deals


def summarize(deals, month_prefix):
    """month_prefix like '04/26' or '05/26'"""
    month_deals = [
        d for d in deals
        if d["date"].endswith(month_prefix) and not d["special"]
    ]
    if not month_deals:
        return None
    areas = [d["area"] for d in month_deals]
    psfs = [d["psf"] for d in month_deals]
    total_price = sum(d["area"] * d["psf"] for d in month_deals)
    total_area = sum(areas)
    return {
        "count": len(month_deals),
        "psf_min": min(psfs),
        "psf_max": max(psfs),
        "psf_avg": round(total_price / total_area),
        "area_min": min(areas),
        "area_max": max(areas),
        "deals": month_deals,
    }


def search_estate(name):
    url = "https://www.midland.com.hk/zh-hk/search/estate?q=" + quote(name)
    html = fetch(url)
    links = re.findall(r"/zh-hk/estate/[^\"']+?-(E[0-9A-Z]+)", html)
    return list(dict.fromkeys(links))[:5]


if __name__ == "__main__":
    print("=== SEARCH ===")
    for n in SEARCH_NAMES:
        try:
            links = search_estate(n)
            print(n, links)
        except Exception as e:
            print(n, "ERR", e)

    print("\n=== PARSE ===")
    for e in ESTATES:
        html = fetch(e["url"])
        deals = parse_midland_transactions(html)
        print(e["name"], "total", len(deals))
        for m in ["04/26", "05/26"]:
            s = summarize(deals, m)
            print(" ", m, s)
