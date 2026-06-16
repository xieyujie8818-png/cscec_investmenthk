# -*- coding: utf-8 -*-
"""Fetch Apr/May 2026 transactions from Midland estate pages."""
import json
import re
import urllib.request

ESTATE_URLS = {
    "大埔寶馬山": "https://www.midland.com.hk/zh-hk/estate/%E6%96%B0%E7%95%8C-%E5%A4%A7%E5%9F%94%E5%8D%8A%E5%B1%B1-%E5%A4%A7%E5%9F%94%E5%AF%B6%E9%A6%AC%E5%B1%B1-E11504",
    "天鑽": "https://www.midland.com.hk/zh-hk/estate/%E6%96%B0%E7%95%8C-%E5%A4%A7%E5%9F%94%E5%8D%8A%E5%B1%B1-%E5%A4%A9%E9%91%BD-E000016716",
    "悠然山莊": "https://www.midland.com.hk/zh-hk/estate/%E6%96%B0%E7%95%8C-%E5%A4%A7%E5%9F%94%E5%8D%8A%E5%B1%B1-%E6%82%A0%E7%84%B6%E5%B1%B1%E8%8E%8A-E11506",
    "雍怡雅苑": "https://www.midland.com.hk/zh-hk/estate/%E6%96%B0%E7%95%8C-%E5%A4%A7%E5%9F%94%E5%8D%8A%E5%B1%B1-%E9%9B%8D%E6%80%A1%E9%9B%85%E8%8B%91-E11509",
    "翡翠花園": "https://www.midland.com.hk/zh-hk/estate/%E6%96%B0%E7%95%8C-%E5%A4%A7%E5%9F%94%E5%8D%8A%E5%B1%B1-%E7%BF%A0%E7%BF%A0%E8%8A%B1%E5%9C%92-E11510",
    "疊翠豪庭": "https://www.midland.com.hk/zh-hk/estate/%E6%96%B0%E7%95%8C-%E5%A4%A7%E5%9F%94%E5%8D%8A%E5%B1%B1-%E7%96%8A%E7%BF%A0%E8%B1%AA%E5%BA%AD-E11511",
    "泓山": "https://www.midland.com.hk/zh-hk/estate/%E6%96%B0%E7%95%8C-%E5%A4%A7%E5%9F%94%E5%8D%8A%E5%B1%B1-%E6%B3%93%E5%B1%B1-E000004059",
    "逍遙雋岸": "https://www.midland.com.hk/zh-hk/estate/%E6%96%B0%E7%95%8C-%E5%A4%A7%E5%9F%94%E5%8D%8A%E5%B1%B1-%E9%80%8D%E9%81%99%E9%9B%8B%E5%B2%B8-E000004058",
}


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def parse_transactions(html: str):
    rows = []
    # Pattern: DD/MM/26 ... 實NNN呎 ... @$PSF
    for m in re.finditer(
        r"(\d{2})/(\d{2})/26[^$]{0,300}?實(\d+)呎[^$]{0,120}?@\$(\d[\d,]*)",
        html,
    ):
        day, mon, area, psf = m.group(1), m.group(2), int(m.group(3)), int(m.group(4).replace(",", ""))
        if area < 200 or psf < 3000:
            continue
        rows.append(
            {
                "date": f"2026-{mon}-{day}",
                "area": area,
                "psf": psf,
            }
        )
    # dedupe
    seen = set()
    out = []
    for r in rows:
        k = (r["date"], r["area"], r["psf"])
        if k in seen:
            continue
        seen.add(k)
        out.append(r)
    return sorted(out, key=lambda x: x["date"])


def summarize(rows, month_prefix):
    mrows = [r for r in rows if r["date"].startswith(month_prefix)]
    if not mrows:
        return None
    areas = [r["area"] for r in mrows]
    psfs = [r["psf"] for r in mrows]
    wsum = sum(r["area"] * r["psf"] for r in mrows)
    warea = sum(areas)
    return {
        "count": len(mrows),
        "psf_min": min(psfs),
        "psf_max": max(psfs),
        "psf_avg": round(wsum / warea),
        "area_min": min(areas),
        "area_max": max(areas),
        "rows": mrows,
    }


def main():
    result = {}
    for name, url in ESTATE_URLS.items():
        try:
            html = fetch(url)
            rows = parse_transactions(html)
            result[name] = {
                "url": url,
                "all_recent": rows[:15],
                "apr": summarize(rows, "2026-04"),
                "may": summarize(rows, "2026-05"),
            }
        except Exception as e:
            result[name] = {"error": str(e), "url": url}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
