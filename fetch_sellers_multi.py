"""Try multiple read-only paths for Ozon competitor seller names."""
import json
import re
from pathlib import Path

OUT = Path(r"C:\Users\Alex\ozon_analytics")

PIDS = {
    "NK5415": 255832676,
    "NK54125": 306414751,
    "I-D-P": 1424446737,
    "NL24": 306414721,
    "NK6115": 306414710,
}

SELLER_PATS = [
    r'"sellerName"\s*:\s*"([^"]{2,80})"',
    r'"seller_name"\s*:\s*"([^"]{2,80})"',
    r'"brandName"\s*:\s*"([^"]{2,80})"',
    r'"brand_name"\s*:\s*"([^"]{2,80})"',
    r'"sellerTitle"\s*:\s*"([^"]{2,80})"',
    r'"companyName"\s*:\s*"([^"]{2,80})"',
    r'"tradeMark"\s*:\s*"([^"]{2,80})"',
]


def sellers_from(text: str):
    out = []
    for p in SELLER_PATS:
        out.extend(re.findall(p, text))
    return list(dict.fromkeys(out))[:20]


def try_curl_cffi():
    try:
        from curl_cffi import requests as cr
    except ImportError:
        print("curl_cffi not installed")
        return {}
    res = {}
    for offer, pid in PIDS.items():
        urls = [
            f"https://www.ozon.ru/api/composer-api.bx/page/json/v2?url=/product/{pid}/",
            f"https://www.ozon.ru/product/{pid}/",
            f"https://www.ozon.ru/api/seo/product/{pid}",
        ]
        entry = {}
        for url in urls:
            try:
                r = cr.get(url, impersonate="chrome124", timeout=25, headers={
                    "Accept": "text/html,application/json",
                    "Accept-Language": "ru-RU,ru;q=0.9",
                })
                entry[url] = {
                    "status": r.status_code,
                    "len": len(r.text),
                    "sellers": sellers_from(r.text),
                }
                print("curl", offer, url.split("/")[-1] or "root", r.status_code, len(r.text), entry[url]["sellers"][:5])
            except Exception as e:
                entry[url] = {"error": str(e)}
                print("curl ERR", offer, url, e)
        res[offer] = entry
    return res


def try_playwright_headless():
    from playwright.sync_api import sync_playwright
    res = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        context = browser.new_context(
            locale="ru-RU",
            timezone_id="Europe/Moscow",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
            ),
            extra_http_headers={"Accept-Language": "ru-RU,ru;q=0.9"},
        )
        context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")
        page = context.new_page()
        for offer, pid in PIDS.items():
            entry = {}
            for label, url in [
                ("product", f"https://www.ozon.ru/product/{pid}/"),
                ("composer", f"https://www.ozon.ru/api/composer-api.bx/page/json/v2?url=/product/{pid}/"),
            ]:
                try:
                    resp = page.goto(url, wait_until="domcontentloaded", timeout=45000)
                    page.wait_for_timeout(3500)
                    html = page.content()
                    status = resp.status if resp else None
                    sl = sellers_from(html)
                    entry[label] = {"status": status, "len": len(html), "title": page.title(), "sellers": sl}
                    print("pw", offer, label, status, len(html), sl[:5])
                except Exception as e:
                    entry[label] = {"error": str(e)}
                    print("pw ERR", offer, label, e)
            res[offer] = entry
        browser.close()
    return res


def main():
    out = {"curl_cffi": try_curl_cffi(), "playwright": try_playwright_headless()}
    json.dump(out, open(OUT / "competitors_sellers3.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    # summary
    named = 0
    for src in out.values():
        for offer, entry in src.items():
            for v in entry.values():
                if isinstance(v, dict) and v.get("sellers"):
                    named += 1
                    break
    print("entries with seller names:", named)
    print("wrote competitors_sellers3.json")


if __name__ == "__main__":
    main()
