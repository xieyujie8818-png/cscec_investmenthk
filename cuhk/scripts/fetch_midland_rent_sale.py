# -*- coding: utf-8 -*-
"""Fetch Midland estate pages: Apr/May 2026 rent + sale summaries."""
import json
import re
import urllib.request
from pathlib import Path

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

ESTATES = [
    ("大埔寶馬山", "https://www.midland.com.hk/zh-hk/estate/%E6%96%B0%E7%95%8C-%E5%A4%A7%E5%9F%94%E5%8D%8A%E5%B1%B1-%E5%A4%A7%E5%9F%94%E5%AF%B6%E9%A6%AC%E5%B1%B1-E11504"),
    ("悠然山莊", "https://www.midland.com.hk/zh-hk/estate/%E6%96%B0%E7%95%8C-%E5%A4%A7%E5%9F%94%E5%8D%8A%E5%B1%B1-%E6%82%A0%E7%84%B6%E5%B1%B1%E8%8E%8A-E11584"),
    ("天鑽", "https://www.midland.com.hk/zh-hk/estate/%E6%96%B0%E7%95%8C-%E5%A4%A7%E5%9F%94%E5%8D%8A%E5%B1%B1-%E5%A4%A9%E9%91%BD-E000016716"),
    ("雍怡雅苑", "https://www.midland.com.hk/zh-hk/estate/%E6%96%B0%E7%95%8C-%E5%A4%A7%E5%9F%94%E5%8D%8A%E5%B1%B1-%E9%9B%8D%E6%80%A1%E9%9B%85%E8%8B%91-E11509"),
    ("偉東·雍宜山莊", None),
    ("翡翠花園", "https://www.midland.com.hk/zh-hk/estate/%E6%96%B0%E7%95%8C-%E5%A4%A7%E5%9F%94%E5%8D%8A%E5%B1%B1-%E7%BF%A0%E7%BF%A0%E8%8A%B1%E5%9C%92-E11510"),
    ("疊翠豪庭", "https://www.midland.com.hk/zh-hk/estate/%E6%96%B0%E7%95%8C-%E5%A4%A7%E5%9F%94%E5%8D%8A%E5%B1%B1-%E7%96%8A%E7%BF%A0%E8%B1%AA%E5%BA%AD-E11511"),
    ("泓山", "https://www.midland.com.hk/zh-hk/estate/%E6%96%B0%E7%95%8C-%E5%A4%A7%E5%9F%94%E5%8D%8A%E5%B1%B1-%E6%B3%93%E5%B1%B1-E000004059"),
    ("逍遙雋岸", "https://www.midland.com.hk/zh-hk/estate/%E6%96%B0%E7%95%8C-%E5%A4%A7%E5%9F%94%E5%8D%8A%E5%B1%B1-%E9%80%8D%E9%81%99%E9%9B%8B%E5%B2%B8-E000004058"),
    ("峰林", None),
    ("史提福樓", None),
    ("僑東·羅宜山莊", None),
    ("盈峰翠邸", "https://www.midland.com.hk/zh-hk/estate/%E6%96%B0%E7%95%8C-%E5%A4%A7%E5%9F%94%E5%8D%8A%E5%B1%B1-%E7%9B%88%E5%B3%B0%E7%BF%A0%E9%82%B7-E11514"),
]


def fetch(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read().decode("utf-8", "replace")


def month_key(date_str):
    """DD/MM/26 -> '04' or '05'"""
    parts = date_str.split("/")
    if len(parts) >= 2:
        return parts[1]
    return None


def parse_sales(html):
    deals = []
    # sale: 18/05/26...實996呎...@$10,442
    for m in re.finditer(
        r"(\d{2}/\d{2}/26)[^$]{0,300}?實(\d+)呎[^$]{0,120}?@\$([\d,]+)",
        html,
    ):
        d, area, psf = m.group(1), int(m.group(2)), int(m.group(3).replace(",", ""))
        if psf < 5000:
            continue
        deals.append(
            {
                "date": d,
                "month": month_key(d),
                "area": area,
                "psf": psf,
                "special": "^" in m.group(0) or "車位" in m.group(0)[:80],
            }
        )
    return deals


def parse_rent_tx(html):
    """Registered rent transactions: $2萬@$38 or $15,500/月@$41"""
    deals = []
    for m in re.finditer(
        r"(\d{2}/\d{2}/26)[^$]{0,300}?實(\d+)呎[^$]{0,80}?\$([\d,]+(?:\.\d+)?)萬[^$]{0,40}?@\$([\d,]+)",
        html,
    ):
        d, area = m.group(1), int(m.group(2))
        rent_wan = float(m.group(3).replace(",", ""))
        psf = int(m.group(4).replace(",", ""))
        if psf > 200:  # likely sale not rent
            continue
        deals.append(
            {
                "date": d,
                "month": month_key(d),
                "area": area,
                "rent_monthly": int(rent_wan * 10000),
                "psf_rent": psf,
            }
        )
    # alt: $23,000/月@$37
    for m in re.finditer(
        r"(\d{2}/\d{2}/26)[^$]{0,300}?實(\d+)呎[^$]{0,80}?\$([\d,]+)/月@\$([\d,]+)",
        html,
    ):
        d, area = m.group(1), int(m.group(2))
        rent = int(m.group(3).replace(",", ""))
        psf = int(m.group(4).replace(",", ""))
        deals.append(
            {
                "date": d,
                "month": month_key(d),
                "area": area,
                "rent_monthly": rent,
                "psf_rent": psf,
            }
        )
    return deals


def parse_rent_listings(html):
    """Listing dates 26-04-XX or 26-05-XX with rent"""
    listings = []
    for m in re.finditer(
        r"26-(04|05)-\d{2}[^$]{0,200}?實用\s*(\d+)\s*呎[^$]{0,80}?美聯物業\$([\d,]+)/月@\$([\d,]+)",
        html,
    ):
        listings.append(
            {
                "month": m.group(1),
                "area": int(m.group(2)),
                "rent_monthly": int(m.group(3).replace(",", "")),
                "psf_rent": int(m.group(4).replace(",", "")),
            }
        )
    for m in re.finditer(
        r"26-(04|05)-\d{2}[^$]{0,200}?實用\s*(\d+)\s*呎[^$]{0,80}?美聯物業\$([\d,]+)萬/月@\$([\d,]+)",
        html,
    ):
        listings.append(
            {
                "month": m.group(1),
                "area": int(m.group(2)),
                "rent_monthly": int(float(m.group(3).replace(",", "")) * 10000),
                "psf_rent": int(m.group(4).replace(",", "")),
            }
        )
    # compact format from page text
    for m in re.finditer(
        r"26-(04|05)-\d{2}[^$]{0,120}?實用\s*(\d+)\s*呎[^$]{0,60}?\$([\d,]+)/月@\$([\d,]+)",
        html,
    ):
        listings.append(
            {
                "month": m.group(1),
                "area": int(m.group(2)),
                "rent_monthly": int(m.group(3).replace(",", "")),
                "psf_rent": int(m.group(4).replace(",", "")),
            }
        )
    for m in re.finditer(
        r"(\d{2}/\d{2}/26)[^$]{0,200}?實(\d+)呎[^$]{0,60}?\$([\d,]+)萬@\$([\d,]+)",
        html,
    ):
        psf = int(m.group(4).replace(",", ""))
        if psf >= 200:
            continue
        listings.append(
            {
                "month": month_key(m.group(1)),
                "area": int(m.group(2)),
                "rent_monthly": int(float(m.group(3).replace(",", "")) * 10000),
                "psf_rent": psf,
                "date": m.group(1),
                "type": "rent_tx",
            }
        )
    return listings


def extract_summary(html):
    s = {}
    m = re.search(r"放盤平均呎租\s*\$([\d,]+)", html)
    if m:
        s["listing_avg_psf_rent"] = int(m.group(1).replace(",", ""))
    m = re.search(r"放盤租價\s*\$([\d,]+)\s*-\s*\$([\d,]+)", html)
    if m:
        s["listing_rent_min"] = int(m.group(1).replace(",", ""))
        s["listing_rent_max"] = int(m.group(2).replace(",", ""))
    m = re.search(r"成交平均呎租 \(過去30日\)\s*\$([\d,]+)", html)
    if m:
        s["tx_avg_psf_rent_30d"] = int(m.group(1).replace(",", ""))
    m = re.search(r"(\d+)\s*租盤", html)
    if m:
        s["rent_listings_count"] = int(m.group(1))
    m = re.search(r"(\d+)\s*賣盤", html)
    if m:
        s["sale_listings_count"] = int(m.group(1))
    return s


def summarize_rent(items, month):
    sub = [x for x in items if x.get("month") == month]
    if not sub:
        return None
    rents = [x["rent_monthly"] for x in sub]
    psfs = [x["psf_rent"] for x in sub]
    return {
        "count": len(sub),
        "rent_min": min(rents),
        "rent_max": max(rents),
        "psf_min": min(psfs),
        "psf_max": max(psfs),
        "psf_avg": round(sum(psfs) / len(psfs)),
    }


def summarize_sale(deals, month, exclude_special=True):
    sub = [
        d
        for d in deals
        if d.get("month") == month and (not exclude_special or not d.get("special"))
    ]
    if not sub:
        return None
    psfs = [d["psf"] for d in sub]
    total = sum(d["area"] * d["psf"] for d in sub)
    area_sum = sum(d["area"] for d in sub)
    return {
        "count": len(sub),
        "psf_min": min(psfs),
        "psf_max": max(psfs),
        "psf_avg": round(total / area_sum),
    }


def main():
    out = {}
    for name, url in ESTATES:
        entry = {"url": url}
        if not url:
            out[name] = entry
            continue
        try:
            html = fetch(url)
            entry["title_ok"] = name in html or html[:500]
            entry["summary"] = extract_summary(html)
            sales = parse_sales(html)
            rent_tx = parse_rent_tx(html)
            rent_list = parse_rent_listings(html)
            entry["sales"] = sales
            entry["rent_tx"] = rent_tx
            entry["rent_listings"] = rent_list
            for m in ("04", "05"):
                entry[f"sale_{m}"] = summarize_sale(sales, m)
                rent_items = [r for r in rent_tx if r.get("month") == m]
                if not rent_items:
                    rent_items = [r for r in rent_list if r.get("month") == m]
                entry[f"rent_{m}"] = summarize_rent(rent_items, m)
                entry[f"rent_{m}_source"] = (
                    "租務成交" if any(r.get("month") == m for r in rent_tx) else (
                        "放租叫價" if rent_items else None
                    )
                )
        except Exception as e:
            entry["error"] = str(e)
        out[name] = entry
        print(name, "sales", len(entry.get("sales", [])), "rent_tx", len(entry.get("rent_tx", [])), "rent_list", len(entry.get("rent_listings", [])))

    path = Path(__file__).resolve().parents[1] / "scripts" / "midland_rent_sale.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Wrote", path)


if __name__ == "__main__":
    main()
