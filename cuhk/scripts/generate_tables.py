# -*- coding: utf-8 -*-
"""Generate Apr/May 2026 comparison tables from verified Midland data."""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

ESTATES = [
    {
        "seq": 1,
        "name": "大埔寶馬山",
        "en": "Pacific Palisades",
        "dev": "信和",
        "loc": "山賢路8號",
        "midland_url": "https://www.midland.com.hk/zh-hk/estate/%E6%96%B0%E7%95%8C-%E5%A4%A7%E5%9F%94%E5%8D%8A%E5%B1%B1-%E5%A4%A7%E5%9F%94%E5%AF%B6%E9%A6%AC%E5%B1%B1-E11504",
        "apr": {"deals": [(728, 10440), (756, 10582), (533, 10038), (756, 11376)], "note": "含1宗標示^特殊成交"},
        "may": {"deals": [(996, 10442), (565, 10938)], "note": ""},
        "hket": "",
    },
    {
        "seq": 2,
        "name": "悠然山莊",
        "en": "The Paragon",
        "dev": "加文",
        "loc": "山賢路9號",
        "midland_url": "https://www.midland.com.hk/zh-hk/estate/%E6%96%B0%E7%95%8C-%E5%A4%A7%E5%9F%94%E5%8D%8A%E5%B1%B1-%E6%82%A0%E7%84%B6%E5%B1%B1%E8%8E%8A-E11584",
        "apr": {"deals": [(914, 9497), (913, 9069)], "note": ""},
        "may": {"deals": [], "note": "當月無註冊處成交"},
        "hket": "",
    },
    {
        "seq": 3,
        "name": "天鑽",
        "en": "The Regent",
        "dev": "新鴻基",
        "loc": "創新路1號",
        "midland_url": "https://www.midland.com.hk/zh-hk/estate/%E6%96%B0%E7%95%8C-%E5%A4%A7%E5%9F%94%E5%8D%8A%E5%B1%B1-%E5%A4%A9%E9%91%BD-E000016716",
        "apr": {
            "deals": [
                (457, 13239),
                (735, 13306),
                (457, 13961),
                (525, 12533),
                (457, 15011),
                (524, 13359),
            ],
            "note": "4月28日735呎戶見HKET報道",
        },
        "may": {
            "deals": [
                (551, 13721),
                (584, 13116),
                (775, 12490),
                (524, 13130),
                (748, 12687),
                (735, 13306),
            ],
            "note": "已剔除連車位特殊成交",
        },
        "hket": "https://paper.hket.com/article/4077834/",
    },
    {
        "seq": 4,
        "name": "雍怡雅苑",
        "en": "Chateau Royale",
        "dev": "新鴻基",
        "loc": "雍宜路1號",
        "midland_url": "https://www.midland.com.hk/zh-hk/property/%E6%96%B0%E7%95%8C-%E5%A4%A7%E5%9F%94%E5%8D%8A%E5%B1%B1-%E9%9B%8D%E6%80%A1%E9%9B%85%E8%8B%91%E9%9B%8D%E6%97%A5%E5%BA%AD%E9%9B%8D%E5%AE%9C%E8%B7%AF1%E8%99%9F-%E7%8D%A8%E7%AB%8B%E5%B1%8B-M300300767",
        "apr": {"deals": [], "note": "美聯／HKET 均無2026年4月成交"},
        "may": {"deals": [], "note": "美聯／HKET 均無2026年5月成交"},
        "hket": "",
    },
    {
        "seq": 5,
        "name": "偉東·雍宜山莊",
        "en": "Grand Dynasty View",
        "dev": "—",
        "loc": "下黃宜坳",
        "midland_url": "",
        "apr": {"deals": [], "note": "美聯／HKET 均無2026年4月成交"},
        "may": {"deals": [], "note": "美聯／HKET 均無2026年5月成交"},
        "hket": "",
    },
    {
        "seq": 6,
        "name": "翡翠花園",
        "en": "Savanna Garden",
        "dev": "新鴻基",
        "loc": "大埔公路大埔滘段4283號",
        "midland_url": "",
        "apr": {"deals": [], "note": "美聯／HKET 均無2026年4月成交"},
        "may": {"deals": [], "note": "美聯／HKET 均無2026年5月成交"},
        "hket": "",
    },
    {
        "seq": 7,
        "name": "疊翠豪庭",
        "en": "The Paramount",
        "dev": "—",
        "loc": "大埔公路大埔滘段4188號",
        "midland_url": "",
        "apr": {"deals": [], "note": "美聯／HKET 均無2026年4月成交"},
        "may": {"deals": [], "note": "美聯／HKET 均無2026年5月成交"},
        "hket": "",
    },
    {
        "seq": 8,
        "name": "泓山",
        "en": "The Cavaridge",
        "dev": "建灝",
        "loc": "逸遙路3號",
        "midland_url": "",
        "apr": {"deals": [], "note": "美聯／HKET 均無2026年4月成交"},
        "may": {"deals": [], "note": "美聯／HKET 均無2026年5月成交"},
        "hket": "",
    },
    {
        "seq": 9,
        "name": "逍遙雋岸",
        "en": "L Utopie",
        "dev": "興聯置業",
        "loc": "逸遙路大埔滘段18號",
        "midland_url": "https://www.midland.com.hk/zh-hk/estate/%E6%96%B0%E7%95%8C-%E5%A4%A7%E5%9F%94%E5%8D%8A%E5%B1%B1-%E9%80%8D%E9%81%99%E9%9B%8B%E5%B2%B8-E000004058",
        "apr": {"deals": [], "note": "美聯屋苑專頁無2026年4月成交"},
        "may": {"deals": [], "note": "美聯屋苑專頁無2026年5月成交"},
        "hket": "",
    },
    {
        "seq": 10,
        "name": "峰林",
        "en": "The Peak",
        "dev": "—",
        "loc": "大埔滘",
        "midland_url": "",
        "apr": {"deals": [], "note": "美聯／HKET 均無2026年4月成交"},
        "may": {"deals": [], "note": "美聯／HKET 均無2026年5月成交"},
        "hket": "",
    },
    {
        "seq": 11,
        "name": "史提福樓",
        "en": "Stafford House",
        "dev": "—",
        "loc": "大埔滘新圍",
        "midland_url": "",
        "apr": {"deals": [], "note": "美聯／HKET 均無2026年4月成交"},
        "may": {"deals": [], "note": "美聯／HKET 均無2026年5月成交"},
        "hket": "",
    },
    {
        "seq": 12,
        "name": "僑東·羅宜山莊",
        "en": "Kiu Tung Lo Yee Villa",
        "dev": "—",
        "loc": "大埔滘",
        "midland_url": "",
        "apr": {"deals": [], "note": "美聯／HKET 均無2026年4月成交"},
        "may": {"deals": [], "note": "美聯／HKET 均無2026年5月成交"},
        "hket": "",
    },
]


def summarize(deals):
    if not deals:
        return None
    areas = [d[0] for d in deals]
    psfs = [d[1] for d in deals]
    total = sum(a * p for a, p in deals)
    area_sum = sum(areas)
    return {
        "count": len(deals),
        "psf_min": min(psfs),
        "psf_max": max(psfs),
        "psf_avg": round(total / area_sum),
        "area_min": min(areas),
        "area_max": max(areas),
    }


def fmt_range(lo, hi, suffix=""):
    if lo is None:
        return "—"
    return f"{lo:,} – {hi:,}{suffix}"


def fmt_num(n):
    return "—" if n is None else f"{n:,}"


def build_rows(month_key, month_label):
    rows = []
    for e in ESTATES:
        block = e[month_key]
        s = summarize(block["deals"])
        note = block["note"] or ("當月土地註冊處成交" if s else "")
        src = "美聯物業"
        if e["midland_url"]:
            src += f"（{e['midland_url']}）"
        if month_key == "apr" and e["hket"]:
            src += f"；HKET（{e['hket']}）"
        rows.append(
            {
                "月份": month_label,
                "序號": e["seq"],
                "項目名稱": e["name"],
                "英文名": e["en"],
                "發展商": e["dev"],
                "位置": e["loc"],
                "成交價範圍_元每呎": fmt_range(
                    s["psf_min"] if s else None, s["psf_max"] if s else None
                ),
                "平均成交價_元每呎": fmt_num(s["psf_avg"] if s else None),
                "成交單位面積區間_平方呎": fmt_range(
                    s["area_min"] if s else None,
                    s["area_max"] if s else None,
                    "",
                ),
                "成交量_宗": s["count"] if s else 0,
                "備註": note,
                "資料來源": src,
            }
        )
    return rows


def write_csv():
    rows = build_rows("apr", "2026年4月") + build_rows("may", "2026年5月")
    path = ROOT / "周邊樓盤成交對標表.csv"
    fields = list(rows[0].keys())
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print("Wrote", path)


if __name__ == "__main__":
    write_csv()
    for m in ("apr", "may"):
        active = [e["name"] for e in ESTATES if summarize(e[m]["deals"])]
        print(m, "active:", active)
