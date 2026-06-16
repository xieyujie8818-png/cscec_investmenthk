"""Fetch draft article bodies using daily-brief-app Playwright profiles."""
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "daily-brief-app"
sys.path.insert(0, str(ROOT))

from playwright.async_api import async_playwright  # noqa: E402
from app.fetchers import (  # noqa: E402
    _detect_source_id,
    _get_fetch_context,
    fetch_article_detail,
)

ARTICLES = [
    {"id": "D01", "title": "三方向拓金融中心 深化股債聯動", "url": "https://www.hkej.com/dailynews/headline/article/4431982"},
    {"id": "D02", "title": "金融經貿着重跨市場跨境聯動 把握供應鏈重組及數字化機遇", "url": "https://www.wenweipo.com/a/202606/16/AP6a309380e4b0b49ad1bf873a.html"},
    {"id": "D03", "title": "【中國經濟】內地5月「三頭馬車」數據 工業勝預期、零售及固投遜預期", "url": "https://inews.hket.com/article/4147213"},
    {"id": "D04", "title": "星擬今年推新黃金清算系統 爭港亞太黃金交易樞紐地位", "url": "https://news.mingpao.com/pns/%E7%B6%93%E6%BF%9F/article/20260616/s00004/1781543241580"},
    {"id": "D05", "title": "匯豐恒生網銀昨早出現故障 下午逐步復常 金管局表關注", "url": "https://news.mingpao.com/pns/%E7%B6%93%E6%BF%9F/article/20260616/s00004/1781543239609"},
    {"id": "D06", "title": "【香港經濟】本港迎新一輪清盤潮！顧問FTI：結業潮未停、零售餐飲重災", "url": "https://inews.hket.com/article/4146956"},
    {"id": "D07", "title": "港版五年規劃諮詢 北都提速成首務", "url": "https://paper.hket.com/article/4147038"},
    {"id": "D08", "title": "夏寶龍今明來港兩天 就對接「十五五」及推動北都建設考察調研", "url": "https://www.wenweipo.com/a/202606/16/AP6a309ddee4b0b49ad1bf8887.html"},
    {"id": "D09", "title": "大學紛挺大學城 打造創科人才新高地", "url": "https://www.wenweipo.com/a/202606/16/AP6a306874e4b0b49ad1bf8445.html"},
    {"id": "D10", "title": "北都提速 新地粉嶺北次輪補地價4263萬", "url": "https://paper.hket.com/article/4146981"},
    {"id": "D11", "title": "會德豐古洞項目短期命名 最快7月推", "url": "https://paper.hket.com/article/4146992"},
    {"id": "D12", "title": "天御複式8.8億「賣殼」 內地富豪購入", "url": "https://paper.hket.com/article/4146991"},
    {"id": "D13", "title": "新盤｜波老道「應天」頂層3.62億招標沽出 呎價12.4萬刷新今年一手紀錄", "url": "https://www.wenweipo.com/a/202606/14/AP6a2ebc27e4b0b49ad1bf5cba.html"},
    {"id": "D14", "title": "鍾楚義夫婦逾億沽種植道逾70年豪宅 呎價約3.4萬雙破頂", "url": "https://news.mingpao.com/pns/%E7%B6%93%E6%BF%9F/article/20260616/s00004/1781542120112"},
    {"id": "D15", "title": "柏傲山4房3100萬沽 較同類兩月升11%", "url": "https://paper.hket.com/article/4147039"},
    {"id": "D16", "title": "工商舖首5月2035宗買賣 按年增逾11%", "url": "https://paper.hket.com/article/4146984"},
    {"id": "D17", "title": "啟德天瀧4房6036萬沽 呎價4.3萬", "url": "https://paper.hket.com/article/4146994"},
    {"id": "D18", "title": "十大屋苑轉靜 半月交投挫26%", "url": "https://www.hkej.com/dailynews/property/article/4432023"},
]

OUT = Path(__file__).resolve().parents[1] / "output" / "2026-06-16" / "extracted-articles.json"


async def main() -> None:
    results = []
    async with async_playwright() as pw:
        headless_browser = await pw.chromium.launch(headless=True)
        public_ctx = await headless_browser.new_context()
        for art in ARTICLES:
            sid = _detect_source_id(art["url"])
            needs_login = sid in ("hket", "mingpao", "hkej")
            ctx = public_ctx
            if needs_login:
                ctx = await _get_fetch_context(pw, sid, True, sid)
            try:
                title, body, snippet, pub, raw = await fetch_article_detail(
                    ctx,
                    art["url"],
                    art["title"],
                    sid,
                    pw=pw if needs_login else None,
                    source_name=sid,
                )
                err = "" if len(body.strip()) >= 60 else "body_too_short"
                results.append(
                    {
                        **art,
                        "source_id": sid,
                        "title_fetched": title,
                        "text": body,
                        "snippet": snippet,
                        "pub": pub,
                        "len": len(body),
                        "error": err,
                    }
                )
                print(f"{art['id']} ok len={len(body)}", flush=True)
            except Exception as exc:
                results.append({**art, "error": str(exc), "text": "", "len": 0})
                print(f"{art['id']} FAIL {exc}", flush=True)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    ok = sum(1 for r in results if not r.get("error"))
    print(f"Wrote {len(results)} articles ({ok} ok) to {OUT}")
    await headless_browser.close()


if __name__ == "__main__":
    asyncio.run(main())
