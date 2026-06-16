# -*- coding: utf-8 -*-
"""Fetch Midland rent data for HKU/SYP comparables."""
import json
import re
import urllib.request
from pathlib import Path

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# Estates: name, url, year_completed (for filter)
ESTATES = [
    ("吉喆", "https://www.midland.com.hk/zh-hk/estate/%E6%B8%AF%E5%B3%B6-%E8%A5%BF%E7%87%9F%E7%9B%A4-%E5%90%89%E5%93%8D-E000016198", 2021),
    ("Eight South Lane", "https://www.midland.com.hk/zh-hk/estate/%E6%B8%AF%E5%B3%B6-%E8%A5%BF%E7%87%9F%E7%9B%A4-Eight-South-Lane-E000015985", 2017),
    ("藝里坊．1號", "https://www.midland.com.hk/zh-hk/estate/%E6%B8%AF%E5%B3%B6-%E8%A5%BF%E7%87%9F%E7%9B%A4-%E8%97%9D%E9%87%8C%E5%9D%8A%EF%BC%8E1%E8%99%9F-E000016197", 2020),
    ("翰林峰", "https://www.midland.com.hk/zh-hk/estate/%E6%B8%AF%E5%B3%B6-%E8%A5%BF%E7%87%9F%E7%9B%A4-%E7%BF%B0%E6%9E%97%E5%B3%B0-E000015984", 2019),
    ("曉譽", "https://www.midland.com.hk/zh-hk/estate/%E6%B8%AF%E5%B3%B6-%E8%A5%BF%E7%87%9F%E7%9B%A4-%E6%9B%89%E8%AD%BD-E000013809", 2014),
    # Additional candidates within 15 years near SYP/HKU
    ("尚瓏", "https://www.midland.com.hk/zh-hk/estate/%E6%B8%AF%E5%B3%B6-%E8%A5%BF%E7%87%9F%E7%9B%A4-%E5%B0%9A%E7%93%8F-E000017130", 2022),
    ("懿山", "https://www.midland.com.hk/zh-hk/estate/%E6%B8%AF%E5%B3%B6-%E8%A5%BF%E7%87%9F%E7%9B%A4-%E6%87%BF%E5%B1%B1-E000013810", 2014),
    ("高士台", "https://www.midland.com.hk/zh-hk/estate/%E6%B8%AF%E5%B3%B6-%E8%A5%BF%E7%87%9F%E7%9B%A4-%E9%AB%98%E5%A3%AB%E5%8F%B0-E000014812", 2015),
    ("Kennedy 38", "https://www.midland.com.hk/zh-hk/estate/%E6%B8%AF%E5%B3%B6-%E8%A5%BF%E7%87%9F%E7%9B%A4-Kennedy-38-E000016716", 2021),
    ("63 Pokfulam", "https://www.midland.com.hk/zh-hk/estate/%E6%B8%AF%E5%B3%B6-%E8%A5%BF%E7%87%9F%E7%9B%A4-63-Pokfulam-E000015983", 2017),
    ("瑧蓺", "https://www.midland.com.hk/zh-hk/estate/%E6%B8%AF%E5%B3%B6-%E8%A5%BF%E7%87%9F%E7%9B%A4-%E7%91%A7%E8%93%BA-E000016199", 2021),
    ("尚譽", "https://www.midland.com.hk/zh-hk/estate/%E6%B8%AF%E5%B3%B6-%E4%B8%AD%E8%A5%BF%E5%8D%80-%E5%B0%9A%E8%AD%BD-E000015986", 2017),
    ("瑧逸", "https://www.midland.com.hk/zh-hk/estate/%E6%B8%AF%E5%B3%B6-%E8%A5%BF%E7%87%9F%E7%9B%A4-%E7%91%A7%E9%80%B8-E000016200", 2020),
    ("藝里坊．2號", "https://www.midland.com.hk/zh-hk/estate/%E6%B8%AF%E5%B3%B6-%E8%A5%BF%E7%87%9F%E7%9B%A4-%E8%97%9D%E9%87%8C%E5%9D%8A%EF%BC%8E2%E8%99%9F-E000017131", 2021),
    ("維港峰", "https://www.midland.com.hk/zh-hk/estate/%E6%B8%AF%E5%B3%B6-%E8%A5%BF%E7%87%9F%E7%9B%A4-%E7%B6%AD%E6%B8%AF%E5%B3%B0-E000014811", 2016),
    ("瑧譽", "https://www.midland.com.hk/zh-hk/estate/%E6%B8%AF%E5%B3%B6-%E4%B8%AD%E8%A5%BF%E5%8D%80-%E7%91%A7%E8%AD%BD-E000014810", 2012),
]


def fetch(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read().decode("utf-8", "replace")


def extract_year(html):
    m = re.search(r"落成日期\s*(\d{2}/\d{2}/(\d{4}))", html)
    if m:
        return int(m.group(2))
    m = re.search(r"於(\d{4})年\d+月開始落成", html)
    if m:
        return int(m.group(1))
    return None


def extract_summary(html):
    s = {}
    m = re.search(r"放盤平均呎租\s*\$([\d,]+)", html)
    if m:
        s["listing_avg_psf"] = int(m.group(1).replace(",", ""))
    m = re.search(r"放盤租價\s*\$([\d,]+)\s*-\s*\$([\d,]+)", html)
    if m:
        s["rent_min"] = int(m.group(1).replace(",", ""))
        s["rent_max"] = int(m.group(2).replace(",", ""))
    m = re.search(r"成交平均呎租 \(過去30日\)\s*\$([\d,]+)", html)
    if m:
        s["tx_avg_psf_30d"] = int(m.group(1).replace(",", ""))
    m = re.search(r"(\d+)\s*租盤", html)
    if m:
        s["rent_count"] = int(m.group(1))
    return s


def parse_rent_listings(html):
    """Parse rent listings with room type, area, rent, psf."""
    listings = []
    # Pattern: 開放式/1房/2房 with area and rent
    patterns = [
        r"(開放式|1房|2房|3房)[^$]{0,80}?實用\s*(\d+)\s*呎[^$]{0,80}?\$([\d,]+)/月@\$([\d,]+)",
        r"(開放式|1房|2房|3房)[^$]{0,80}?實(\d+)呎[^$]{0,80}?\$([\d,]+)/月@\$([\d,]+)",
        r"實用\s*(\d+)\s*呎[^$]{0,80}?(開放式|1房|2房|3房)[^$]{0,80}?\$([\d,]+)/月@\$([\d,]+)",
        r"實(\d+)呎[^$]{0,80}?(開放式|1房|2房|3房)[^$]{0,80}?\$([\d,]+)/月@\$([\d,]+)",
    ]
    for pat in patterns:
        for m in re.finditer(pat, html):
            g = m.groups()
            if g[0] in ("開放式", "1房", "2房", "3房"):
                room, area, rent, psf = g[0], int(g[1]), int(g[2].replace(",", "")), int(g[3].replace(",", ""))
            else:
                area, room, rent, psf = int(g[0]), g[1], int(g[2].replace(",", "")), int(g[3].replace(",", ""))
            listings.append({"room": room, "area": area, "rent": rent, "psf": psf})

    # Rent transactions from registry
    for m in re.finditer(
        r"(\d{2}/\d{2}/26)[^$]{0,200}?(開放式|1房|2房|3房)[^$]{0,80}?實(\d+)呎[^$]{0,60}?@\$([\d,]+)",
        html,
    ):
        psf = int(m.group(4).replace(",", ""))
        if psf >= 200:  # sale not rent
            continue
        listings.append({
            "room": m.group(2),
            "area": int(m.group(3)),
            "rent": None,
            "psf": psf,
            "type": "tx",
            "date": m.group(1),
        })
    return listings


def summarize_by_room(listings):
    by_room = {}
    for item in listings:
        room = item["room"]
        if room not in by_room:
            by_room[room] = {"areas": [], "rents": [], "psfs": []}
        by_room[room]["areas"].append(item["area"])
        if item.get("rent"):
            by_room[room]["rents"].append(item["rent"])
        by_room[room]["psfs"].append(item["psf"])

    result = {}
    for room, data in by_room.items():
        if not data["areas"]:
            continue
        entry = {
            "area_min": min(data["areas"]),
            "area_max": max(data["areas"]),
            "psf_min": min(data["psfs"]),
            "psf_max": max(data["psfs"]),
        }
        if data["rents"]:
            entry["rent_min"] = min(data["rents"])
            entry["rent_max"] = max(data["rents"])
        result[room] = entry
    return result


def main():
    out = {}
    for name, url, year_hint in ESTATES:
        entry = {"url": url, "year_hint": year_hint}
        try:
            html = fetch(url)
            if "404" in html[:500] and "找不到" in html:
                entry["error"] = "not found"
                out[name] = entry
                print(name, "NOT FOUND")
                continue
            entry["year"] = extract_year(html) or year_hint
            entry["summary"] = extract_summary(html)
            listings = parse_rent_listings(html)
            entry["listings"] = listings
            entry["by_room"] = summarize_by_room(listings)
            out[name] = entry
            print(
                name,
                "year=", entry["year"],
                "rent_listings=", len(listings),
                "summary=", entry["summary"],
            )
        except Exception as e:
            entry["error"] = str(e)
            out[name] = entry
            print(name, "ERROR:", e)

    path = Path(__file__).parent / "hku_rent_data.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Wrote", path)


if __name__ == "__main__":
    main()
