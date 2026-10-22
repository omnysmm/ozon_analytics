"""Scrape Ozon + WB competitor prices (read-only, human-like browsing)."""
import asyncio
import json
import re
from pathlib import Path

from playwright.async_api import async_playwright

OUT = Path(r"C:\Users\Alex\ozon_analytics")

# top offers by gross
econ = json.load(open(OUT / "sku_economics.json", encoding="utf-8"))
top = econ[:25]

QUERIES = []
for r in top:
    name = r["name"] or r["offer_id"]
    # shorten name for search
    q = name[:60]
    QUERIES.append({"offer_id": r["offer_id"], "query": q, "our_price": r["seller_price_api"] or r["gross_product"]})

# WB queries - same products
WB_QUERIES = [q["query"] for q in QUERIES[:15]]


async def scrape_ozon(page, q):
    url = f"https://www.ozon.ru/search/?from_global=true&text={q}"
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(2500)
        # try to extract product cards via JSON state or DOM
        html = await page.content()
        # generic price scrape
        prices = []
        for m in re.finditer(r'"price"\s*:\s*"?(\d+[\d\s]*(?:[.,]\d+)?)"?', html):
            try:
                prices.append(float(m.group(1).replace(" ", "").replace(",", ".")))
            except Exception:
                pass
        names = re.findall(r'"name"\s*:\s*"([^"]{10,120})"', html)
        return {"query": q, "prices": prices[:20], "names": names[:10], "html_len": len(html)}
    except Exception as e:
        return {"query": q, "error": str(e)}


async def scrape_wb(page, q):
    url = f"https://www.wildberries.ru/catalog/0/search.aspx?search={q}"
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(2500)
        html = await page.content()
        prices = []
        for m in re.finditer(r'"price"\s*:\s*\{[^}]*"basic"\s*:\s*(\d+)', html):
            prices.append(int(m.group(1)))
        for m in re.finditer(r'"total"\s*:\s*(\d+)', html):
            prices.append(int(m.group(1)))
        names = re.findall(r'"name"\s*:\s*"([^"]{8,120})"', html)
        return {"query": q, "prices": prices[:20], "names": names[:10], "html_len": len(html)}
    except Exception as e:
        return {"query": q, "error": str(e)}


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel="chrome")
        context = await browser.new_context(
            viewport={"width": 1366, "height": 900},
            locale="ru-RU",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
        )
        page = await context.new_page()

        ozon_res = []
        for i, q in enumerate(QUERIES[:12]):
            r = await scrape_ozon(page, q["query"])
            r["offer_id"] = q["offer_id"]
            r["our_price"] = q["our_price"]
            ozon_res.append(r)
            print(f"OZON {i+1}/{min(12,len(QUERIES))} {q['query'][:40]} prices={r.get('prices',[])[:5]} err={r.get('error')}", flush=True)
            await page.wait_for_timeout(1200)

        wb_res = []
        for i, q in enumerate(WB_QUERIES[:10]):
            r = await scrape_wb(page, q)
            wb_res.append(r)
            print(f"WB {i+1} {q[:40]} prices={r.get('prices',[])[:5]} err={r.get('error')}", flush=True)
            await page.wait_for_timeout(1200)

        json.dump(ozon_res, open(OUT / "competitors_ozon.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        json.dump(wb_res, open(OUT / "competitors_wb.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

        await page.screenshot(path=str(OUT / "competitors_sample.png"))
        await browser.close()
        print("DONE")


if __name__ == "__main__":
    asyncio.run(main())
