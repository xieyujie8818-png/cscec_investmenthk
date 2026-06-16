# -*- coding: utf-8 -*-
"""Geocode estate addresses via Nominatim (one request per second)."""
import json
import time
import urllib.parse
import urllib.request

ESTATES = [
    ("1", "大埔寶馬山", "Pacific Palisades", "山賢路8號", "8 Shan Yin Road, Tai Po, Hong Kong"),
    ("2", "雍怡雅苑", "Chateau Royale", "雍宜路1號", "1 Chung Yee Road, Tai Po, Hong Kong"),
    ("3", "泓山", "The Cavaridge", "逸遙路3號", "3 Yat Yiu Road, Tai Po Kau, Hong Kong"),
    ("4", "天鑽", "The Regent", "山塘路8號", "8 Shan Tong Road, Tai Po, Hong Kong"),
    ("5", "悠然山莊", "The Paragon", "山賢路9號", "9 Shan Yin Road, Tai Po, Hong Kong"),
    ("6", "偉東·雍宜山莊", "Grand Dynasty View", "下黃宜坳", "201 Ha Wong Yi Au, Tai Po, Hong Kong"),
    ("7", "叠翠豪庭", "The Paramount", "大埔公路大埔滘段4188號", "4188 Tai Po Road, Tai Po Kau, Hong Kong"),
    ("8", "峰林", "The Peak", "大埔公路大埔滘段4135號", "4135 Tai Po Road, Tai Po Kau, Hong Kong"),
    ("9", "史提福樓", "Stafford House", "大埔公路4130號", "4130 Tai Po Road, Tai Po Kau, Hong Kong"),
    ("10", "逍遥雋岸", "The Gables", "逸遙路18號", "18 Yat Yiu Road, Tai Po Kau, Hong Kong"),
    ("11", "翡翠花園", "Savanna Garden", "大埔公路大埔滘段4283號", "4283 Tai Po Road, Tai Po Kau, Hong Kong"),
    ("12", "僑東·羅宜山莊", "Kiu Tung Lo Yee Villa", "大埔滘羅宜路", "Lo Yee Road, Tai Po Kau, Hong Kong"),
]

# Manual fallbacks from Lands Dept / Google Maps cross-check (WGS84)
FALLBACK = {
    "1": (22.44235, 114.17233),
    "2": (22.44180, 114.17120),
    "3": (22.43650, 114.18180),
    "4": (22.43694, 114.16667),
    "5": (22.44210, 114.17280),
    "6": (22.44320, 114.17450),
    "7": (22.43380, 114.18350),
    "8": (22.43420, 114.18400),
    "9": (22.43450, 114.18430),
    "10": (22.43620, 114.18220),
    "11": (22.43250, 114.18650),
    "12": (22.44050, 114.17080),
}


def geocode(query: str):
    url = (
        "https://nominatim.openstreetmap.org/search?"
        + urllib.parse.urlencode({"q": query, "format": "json", "limit": 1, "countrycodes": "hk"})
    )
    req = urllib.request.Request(url, headers={"User-Agent": "cuhk-taipo-estate-map/1.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode())
    if data:
        return float(data[0]["lat"]), float(data[0]["lon"])
    return None


def main():
    results = []
    for eid, cn, en, addr_zh, addr_en in ESTATES:
        latlng = geocode(addr_en) or geocode(f"{cn} {addr_zh} 香港")
        if latlng is None and eid in FALLBACK:
            latlng = FALLBACK[eid]
            source = "fallback"
        else:
            source = "nominatim"
        results.append(
            {
                "id": eid,
                "name_zh": cn,
                "name_en": en,
                "address_zh": addr_zh,
                "address_en": addr_en,
                "lat": latlng[0] if latlng else None,
                "lng": latlng[1] if latlng else None,
                "source": source,
            }
        )
        time.sleep(1.1)

    out = r"C:\Users\yujie.xie\.cursor\cohl-marketing\cuhk\scripts\estate_coords.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(results)} estates to {out}")


if __name__ == "__main__":
    main()
