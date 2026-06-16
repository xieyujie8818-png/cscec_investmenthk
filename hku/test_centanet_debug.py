# -*- coding: utf-8 -*-
import json
from playwright.sync_api import sync_playwright

from build_centanet_tx import CLICK_RENT_JS, COLLECT_LINKS_JS, PARSE_DETAIL_JS

url = "https://hk.centanet.com/findproperty/zh-cn/list/transaction/%E5%90%89%E5%96%86_2-SSSPWWPSWS"
candidates = [
    "https://hk.centanet.com/findproperty/zh-cn/transaction-detail/%E5%90%89%E5%96%86_STT202603R0495",
    "https://hk.centanet.com/findproperty/transaction-detail/%E5%90%89%E5%96%86_STT202603R0495",
    "https://hk.centanet.com/findproperty/zh-cn/transaction-detail/-%E5%90%89%E5%96%86_STT202603R0495",
]

out = {}
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(5000)
    page.evaluate(CLICK_RENT_JS)
    page.wait_for_timeout(3000)
    out["links"] = page.evaluate(COLLECT_LINKS_JS)
    html = page.content()
    import re
    out["ids"] = list(dict.fromkeys(re.findall(r"[A-Z]{3}\d{6}R\d+", html)))[:10]

    for c in candidates:
        try:
            page.goto(c, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2000)
            out[c] = page.evaluate(PARSE_DETAIL_JS)
        except Exception as e:
            out[c] = {"error": str(e)}

    browser.close()

json.dumps(out, ensure_ascii=False)
open("debug_centanet.json", "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=2))
