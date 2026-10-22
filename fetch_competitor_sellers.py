"""Get competitor seller names from Ozon storefront JSON (read-only)."""
import asyncio
import json
import re
from pathlib import Path
from urllib.parse import quote

from playwright.async_api import async_playwright

OUT = Path(r"C:\Users\Alex\ozon_analytics")
econ = json.load(open(OUT / "sku_economics.json", encoding="utf-8"))
prices = json.load(open(OUT / "ozon_prices_full.json", encoding="utf-8"))
price_by_offer = {p["offer_id"]: p for p in prices}

# top by qty
top = sorted(econ, key=lambda r: -(r.get("qty_sold") or 0))[:20]


async def fetch_composer(page, query):
    urls = [
        f"https://www.ozon.ru/api/composer-api.bx/page/json/v2?url=/search/?text={quote(query)}&from_global=true",
        f"https://api.ozon.ru/composer-api.bx/page/json/v2?url=/search/?text={quote(query)}",
    ]
    for u in urls:
        try:
            resp = await page.evaluate(
                """async (url) => {
                    const r = await fetch(url, {credentials:'include'});
                    return {status:r.status, text:(await r.text()).slice(0,400000)};
                }""",
                u,
            )
            if resp["status"] == 200 and resp["text"] and resp["text"].strip()[0] in "{[":
                return resp["text"]
        except Exception as e:
            print("fetch err", u[:60], e)
    return None


def extract_sellers_from_json(text):
    """Pull product titles + seller names + prices from composer/search state."""
    out = []
    # try parse as JSON first
    try:
        data = json.loads(text)
    except Exception:
        data = None

    def walk(obj, bag):
        if isinstance(obj, dict):
            # common ozon search item shapes
            name = obj.get("mainState") or obj.get("info") or obj.get("tileImage") or {}
            title = (
                obj.get("title")
                or obj.get("name")
                or (obj.get("info") or {}).get("name")
                or (obj.get("mainState") or [{}])
            )
            if isinstance(title, list):
                title = None
            seller = (
                obj.get("sellerName")
                or obj.get("seller_name")
                or obj.get("brandName")
                or obj.get("brand")
                or (obj.get("seller") or {}).get("name")
                or (obj.get("seller") or {}).get("title")
            )
            price = obj.get("price") or obj.get("finalPrice") or obj.get("atom")
            if isinstance(price, dict):
                price = price.get("value") or price.get("price")
            if isinstance(title, str) and title and (seller or price):
                bag.append({"title": title[:120], "seller": seller, "price": price})
            for v in obj.values():
                walk(v, bag)
        elif isinstance(obj, list):
            for v in obj:
                walk(v, bag)

    bag = []
    if data is not None:
        walk(data, bag)

    # regex fallback for seller-like fields
    if not bag:
        for m in re.finditer(r'"(?:sellerName|seller_name|brandName|brand)"\s*:\s*"([^"]{2,80})"', text):
            bag.append({"title": None, "seller": m.group(1), "price": None})
        for m in re.finditer(r'"(?:title|name)"\s*:\s*"([^"]{15,100})"', text):
            bag.append({"title": m.group(1), "seller": None, "price": None})

    # dedupe by seller
    seen = set()
    uniq = []
    for b in bag:
        key = (b.get("seller"), b.get("title"))
        if key in seen:
            continue
        seen.add(key)
        uniq.append(b)
    return uniq[:30]


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel="chrome")
        context = await browser.new_context(
            locale="ru-RU",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
            viewport={"width": 1366, "height": 900},
        )
        page = await context.new_page()
        # warm up cookies
        await page.goto("https://www.ozon.ru/", wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(2000)

        results = {}
        for item in top[:12]:
            q = (item.get("name") or item["offer_id"])[:50]
            text = await fetch_composer(page, q)
            sellers = extract_sellers_from_json(text) if text else []
            results[item["offer_id"]] = {
                "query": q,
                "found": len(sellers),
                "items": sellers[:15],
                "raw_len": len(text or ""),
            }
            print(f"{item['offer_id']:16s} raw={len(text or '')} sellers={len(sellers)}", flush=True)
            if sellers:
                for s in sellers[:5]:
                    print("   ", s, flush=True)
            await page.wait_for_timeout(800)

        json.dump(results, open(OUT / "competitors_sellers.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        await browser.close()
        print("DONE")


if __name__ == "__main__":
    asyncio.run(main())
