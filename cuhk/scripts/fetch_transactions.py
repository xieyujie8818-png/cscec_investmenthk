# -*- coding: utf-8 -*-
import re
import urllib.request
from urllib.parse import quote

ESTATES = [
    {
        "cn": "大埔寶馬山",
        "en": "Pacific Palisades",
        "dev": "信和",
        "loc": "山賢路8號",
        "units": 547,
        "year": 1997,
    },
    {
        "cn": "雍怡雅苑",
        "en": "Chateau Royale",
        "dev": "—",
        "loc": "大埔滘",
        "units": 0,
        "year": 0,
    },
    {
        "cn": "泓山",
        "en": "The Cavaridge",
        "dev": "—",
        "loc": "逸遙路",
        "units": 13,
        "year": 2006,
    },
    {
        "cn": "天鑽",
        "en": "The Regent",
        "dev": "新鴻基",
        "loc": "創新路1號",
        "units": 1620,
        "year": 2020,
    },
    {
        "cn": "悠然山莊",
        "en": "The Paragon",
        "dev": "加文",
        "loc": "山賢路9號",
        "units": 242,
        "year": 1997,
    },
    {
        "cn": "偉東雍宜山莊",
        "en": "Grand Dynasty View",
        "dev": "—",
        "loc": "下黃宜坳",
        "units": 32,
        "year": 0,
    },
    {
        "cn": "疊翠豪庭",
        "en": "The Paramount",
        "dev": "—",
        "loc": "大埔公路大埔滘段4188號",
        "units": 42,
        "year": 2000,
    },
    {
        "cn": "峰林",
        "en": "The Peak",
        "dev": "—",
        "loc": "大埔滘",
        "units": 0,
        "year": 0,
    },
    {
        "cn": "史提福樓",
        "en": "Stafford House",
        "dev": "—",
        "loc": "大埔滘",
        "units": 0,
        "year": 0,
    },
    {
        "cn": "逍遙雋岸",
        "en": "The Gables",
        "dev": "—",
        "loc": "逸遙路",
        "units": 16,
        "year": 2006,
    },
    {
        "cn": "翡翠花園",
        "en": "Savanna Garden",
        "dev": "新鴻基",
        "loc": "大埔公路大埔滘段4283號",
        "units": 284,
        "year": 1988,
    },
    {
        "cn": "僑東羅宜山莊",
        "en": "Kiu Tung Lo Yee Villa",
        "dev": "—",
        "loc": "大埔滘",
        "units": 0,
        "year": 0,
    },
]

TARGET_MONTH = "2026-05"


def fetch_estate(name: str) -> str:
    url = "https://www.property.hk/tran/a3b" + quote(name) + "$d300o2oa1od103w1yr5/"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=25) as resp:
        return resp.read().decode("utf-8", errors="replace")


def parse_rows(content: str, estate_cn: str):
    rows = []
    for block in re.findall(
        rf"{re.escape(estate_cn)}.*?(\d{{4}}-\d{{2}}-\d{{2}}).*?(\d{{2,4}})\s+(\d+\.\d{{4}})\s+(\d+)",
        content,
    ):
        date, area, price_m, psf = block[0], int(block[1]), float(block[2]), int(block[3])
        if area < 200 or price_m < 1.0 or psf < 3000:
            continue
        rows.append({"date": date, "area": area, "price_m": price_m, "psf": psf})
    # fallback: parse table rows
    if not rows:
        for m in re.finditer(r"<tr[^>]*>(.*?)</tr>", content, re.S | re.I):
            t = re.sub(r"<[^>]+>", " ", m.group(1))
            t = re.sub(r"\s+", " ", t).strip()
            if estate_cn not in t:
                continue
            dm = re.search(r"(20\d{2}-\d{2}-\d{2})", t)
            pm = re.search(r"(\d{2,4})\s+(\d+\.\d{4})\s+(\d+)", t)
            if dm and pm:
                area, price_m, psf = int(pm.group(1)), float(pm.group(2)), int(pm.group(3))
                if area >= 200 and price_m >= 1.0 and psf >= 3000:
                    rows.append(
                        {
                            "date": dm.group(1),
                            "area": area,
                            "price_m": price_m,
                            "psf": psf,
                        }
                    )
    # dedupe
    seen = set()
    out = []
    for r in rows:
        key = (r["date"], r["area"], r["psf"])
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return sorted(out, key=lambda x: x["date"], reverse=True)


def summarize(rows, month):
    month_rows = [r for r in rows if r["date"].startswith(month)]
    if not month_rows:
        return None
    areas = [r["area"] for r in month_rows]
    psfs = [r["psf"] for r in month_rows]
    wsum = sum(r["area"] * r["psf"] for r in month_rows)
    warea = sum(r["area"] for r in month_rows)
    return {
        "count": len(month_rows),
        "psf_min": min(psfs),
        "psf_max": max(psfs),
        "psf_avg": round(wsum / warea),
        "area_min": min(areas),
        "area_max": max(areas),
        "rows": month_rows,
    }


def main():
    for e in ESTATES:
        try:
            html = fetch_estate(e["cn"])
            rows = parse_rows(html, e["cn"])
            s = summarize(rows, TARGET_MONTH)
            print(f"### {e['cn']} ({e['en']})")
            print(f"URL rows total: {len(rows)}")
            if s:
                print(
                    f"MAY: count={s['count']} psf={s['psf_min']}-{s['psf_max']} avg={s['psf_avg']} area={s['area_min']}-{s['area_max']}"
                )
                for r in s["rows"]:
                    print(" ", r)
            else:
                recent = [r for r in rows if r["date"].startswith("2026")][:5]
                print("NO MAY")
                for r in recent:
                    print(" ", r)
        except Exception as ex:
            print(f"### {e['cn']} ERROR {ex}")


if __name__ == "__main__":
    main()
