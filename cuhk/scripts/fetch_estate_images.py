# -*- coding: utf-8 -*-
"""Download estate cover images from Midland estate pages."""
from __future__ import annotations

import html
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "assets" / "estates"

# Estate code embedded in Midland outlook photo paths.
ESTATE_CODES = {
    "天鑽": "EE000016716",
    "雲滙": "EE000016471",
    "海日灣II": "EE000016718",
    "大埔寶馬山": "EE11504",
    "雍怡雅苑": "EE11509",
    "悠然山莊": "EE11584",
}

ESTATES = {
    "天鑽": "https://www.midland.com.hk/zh-hk/estate/%E6%96%B0%E7%95%8C-%E5%A4%A7%E5%9F%94%E5%8D%8A%E5%B1%B1-%E5%A4%A9%E9%91%BD-E000016716",
    "雲滙": "https://www.midland.com.hk/zh-hk/estate/%E6%96%B0%E7%95%8C-%E7%99%BD%E7%9F%B3%E8%A7%92-%E9%9B%B2%E6%BB%99-E000016471",
    "海日灣II": "https://www.midland.com.hk/zh-hk/estate/%E6%96%B0%E7%95%8C-%E7%99%BD%E7%9F%B3%E8%A7%92-%E6%B5%B7%E6%97%A5%E7%81%A3II-E000016718",
    "大埔寶馬山": "https://www.midland.com.hk/zh-hk/estate/%E6%96%B0%E7%95%8C-%E5%A4%A7%E5%9F%94%E5%8D%8A%E5%B1%B1-%E5%A4%A7%E5%9F%94%E5%AF%B6%E9%A6%AC%E5%B1%B1-E11504",
    "雍怡雅苑": "https://www.midland.com.hk/zh-hk/estate/%E6%96%B0%E7%95%8C-%E5%A4%A7%E5%9F%94%E5%8D%8A%E5%B1%B1-%E9%9B%8D%E6%80%A1%E9%9B%85%E8%8B%91-E11509",
    "悠然山莊": "https://www.midland.com.hk/zh-hk/estate/%E6%96%B0%E7%95%8C-%E5%A4%A7%E5%9F%94%E5%8D%8A%E5%B1%B1-%E6%82%A0%E7%84%B6%E5%B1%B1%E8%8E%8A-E11584",
    "偉東雍宜山莊": "https://www.midland.com.hk/zh-hk/estate/%E6%96%B0%E7%95%8C-%E5%A4%A7%E5%9F%94%E5%8D%8A%E5%B1%B1-%E5%81%89%E6%9D%B1-%E9%9B%8D%E5%AE%9C%E5%B1%B1%E8%8E%8A-E000019483",
}

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; estate-image-fetch/1.0)"}


def normalize_image_url(raw: str) -> str:
    url = html.unescape(raw).replace("\\u002F", "/").replace("\\u0026", "&")
    if "img_wm_revamp.php" in url:
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query)
        src = params.get("src", [None])[0]
        if src:
            return urllib.parse.unquote(src)
    return url


def pick_image(page_html: str) -> str | None:
    for pattern in (
        r'property="og:image" content="([^"]+)"',
        r'"imageUrl":"([^"]+)"',
        r'https://[^"\']+\.(?:jpg|jpeg|png|webp)',
    ):
        matches = re.findall(pattern, page_html, re.I)
        for m in matches:
            url = normalize_image_url(m)
            if any(token in url.lower() for token in ("midland", "cloudfront", "amazonaws", "photo_db")):
                return url
    return None


def candidate_urls(raw: str) -> list[str]:
    primary = normalize_image_url(raw)
    urls = [primary]
    if primary.startswith("http://img.midland.com.hk/"):
        https_src = primary.replace("http://", "https://", 1)
        urls.append(https_src)
        encoded = urllib.parse.quote(https_src, safe="")
        urls.append(f"https://wm-cdn.midland.com.hk/img_wm_revamp.php?wm=mr&src={encoded}")
    return list(dict.fromkeys(urls))


def fetch_bytes(url: str, referer: str | None = None) -> bytes:
    headers = dict(HEADERS)
    if referer:
        headers["Referer"] = referer
    req = urllib.request.Request(url, headers=headers)
    return urllib.request.urlopen(req, timeout=30).read()


def download(url: str, dest: Path, referer: str | None = None) -> None:
    headers = dict(HEADERS)
    if referer:
        headers["Referer"] = referer
    req = urllib.request.Request(url, headers=headers)
    dest.write_bytes(fetch_bytes(url, referer=referer))


def best_outlook_photo(code: str, page_url: str, limit: int = 20) -> tuple[str, bytes] | None:
    best: tuple[str, bytes] | None = None
    for idx in range(1, limit + 1):
        raw = f"https://img.midland.com.hk/photo_db/outlook/estate/{code}_{idx}.jpg"
        for candidate_url in candidate_urls(raw):
            try:
                data = fetch_bytes(candidate_url, referer=page_url)
            except Exception:  # noqa: BLE001
                continue
            if len(data) < 50_000:
                continue
            if best is None or len(data) > len(best[1]):
                best = (candidate_url, data)
    return best


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, dict] = {}

    for name, page_url in ESTATES.items():
        entry: dict = {"page": page_url, "image_url": None, "file": None, "error": None}
        try:
            req = urllib.request.Request(page_url, headers=HEADERS)
            page_html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", errors="replace")
            safe = name.replace("·", "").replace(" ", "")
            dest = OUT_DIR / f"{safe}.jpg"
            saved = False
            code = ESTATE_CODES.get(name)
            if code:
                best = best_outlook_photo(code, page_url)
                if best:
                    entry["image_url"] = best[0]
                    dest.write_bytes(best[1])
                    entry["file"] = str(dest.relative_to(ROOT)).replace("\\", "/")
                    saved = True
            if not saved:
                image_url = pick_image(page_html)
                if not image_url:
                    raise RuntimeError("no image found on page")
                entry["image_url"] = image_url
                ext = ".jpg"
                for candidate in (".webp", ".png", ".jpeg", ".jpg"):
                    if candidate in image_url.lower():
                        ext = candidate
                        break
                dest = OUT_DIR / f"{safe}{ext}"
                last_error: Exception | None = None
                for candidate_url in candidate_urls(image_url):
                    try:
                        download(candidate_url, dest, referer=page_url)
                        entry["image_url"] = candidate_url
                        entry["file"] = str(dest.relative_to(ROOT)).replace("\\", "/")
                        last_error = None
                        break
                    except Exception as exc:  # noqa: BLE001
                        last_error = exc
                if last_error is not None:
                    raise last_error
        except Exception as exc:  # noqa: BLE001
            entry["error"] = str(exc)
        manifest[name] = entry

    meta_path = OUT_DIR / "manifest.json"
    meta_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
