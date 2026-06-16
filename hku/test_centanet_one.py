# -*- coding: utf-8 -*-
import json
from build_centanet_tx import scrape_project
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    res = scrape_project(page, "吉喆", "%E5%90%89%E5%96%86_2-SSSPWWPSWS", "")
    browser.close()

Path = __import__("pathlib").Path
Path("test_one.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
