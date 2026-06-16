# -*- coding: utf-8 -*-
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
BASE = "https://hk.centanet.com/findproperty/zh-cn/list/transaction/"

SLUGS = {
    "吉喆": "%E5%90%89%E5%96%86_2-SSSPWWPSWS",
    "翰林峰": "%E7%BF%B0%E6%9E%97%E5%B3%B0_2-SSPPWWPOWG",
    "Kennedy 38": "KENNEDY%2038_2-SSSPWWPVWS",
    "嘉林閣": "%E5%98%89%E6%9E%97%E9%96%A3_2-SDBBPPKJPS",
    "碧瑤灣": "%E7%A2%A7%E7%91%B6%E6%B9%BE_2-OJQCFRCORO?q=udjgk03it5jzb",
    "Victoria Coast": "-Victoria%20Coast_2-SDPPWWPOWS",
    "豪峰II": "Royalton-II_2-SDPPWWPJWS",
    "美林園": "%E7%BE%8E%E7%90%B3%E5%9C%92_1-TITNZHTXHT",
}

out = {}
for name, slug in SLUGS.items():
    url = BASE + slug
    html = urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=30).read().decode("utf-8", "replace")
    ids = list(dict.fromkeys(re.findall(r"[A-Z]{3}\d{6}R\d+", html)))
    paths = list(dict.fromkeys(re.findall(r"transaction-detail/[^\"'\\]+", html)))
    out[name] = {"url": url, "rent_ids": ids[:15], "paths": paths[:5], "rent_count": len(ids)}

Path("centanet_list_probe.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
print("done")
