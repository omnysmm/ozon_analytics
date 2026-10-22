"""Scrape Ozon search DOM for competitor titles/sellers/prices (read-only)."""
import asyncio
import json
import re
from pathlib import Path
from urllib.parse import quote

from playwright.async_api import async_playwright

OUT = Path(r"C:\Users\Alex\ozon_analytics")
econ = json.load(open(OUT / "sku_economics.json", encoding="utf-8"))
top = sorted(econ, key=lambda r: -(r.get("qty_sold") or 0))[:15]


async def scrape_search(page, query):
    url = f"https://www.ozon.ru/search/?text={quote(query)}&from_global=true"
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=50000)
        await page.wait_for_timeout(3500)
        # scroll a bit
        await page.mouse.wheel(0, 1200)
        await page.wait_for_timeout(1500)
    except Exception as e:
        return {"error": str(e), "items": []}

    items = await page.evaluate(
        """() => {
          const out = [];
          const cards = document.querySelectorAll('div.tile, div[data-index], a[href*="/product/"]');
          const seen = new Set();
          cards.forEach((el, i) => {
            if (i > 40) return;
            const a = el.matches('a[href*="/product/"]') ? el : el.querySelector('a[href*="/product/"]');
            const href = a ? a.getAttribute('href') : null;
            const text = (el.innerText || '').split('\\n').map(s => s.trim()).filter(Boolean);
            // find price-like tokens
            let price = null;
            let name = null;
            let brand = null;
            for (const t of text) {
              const m = t.match(/^(\\d[\\d\\s]{2,9})\\s*[₽р]?/);
              if (m && !price) price = parseInt(m[1].replace(/\\s/g,''), 10);
            }
            // first long text is usually name
            for (const t of text) {
              if (t.length > 18 && t.length < 140 && !/^[\\d\\s₽р.,%]+$/.test(t) && !/^\\d+$/.test(t)) {
                name = t; break;
              }
            }
            // seller often appears as short label after brand
            const html = el.innerHTML || '';
            const sm = html.match(/Продавец[^<]{0,40}<\\/[^>]+>\\s*<?[^>]*>([^<]{2,60})/i)
                   || html.match(/seller[^>]{0,40}>([A-Za-zА-Яа-яЁё0-9 \\-]{3,40})</i);
            if (sm) brand = sm[1].trim();
            const key = (href||'') + '|' + (name||'');
            if (key && !seen.has(key) && (name || price)) {
              seen.add(key);
              out.push({href, name, price, seller: brand, snippet: text.slice(0, 8)});
            }
          });
          return out;
        }"""
    )

    # fallback: parse page content for structured seller names
    html = await page.content()
    sellers = re.findall(r'"(?:sellerName|seller_name|brandName|brandTitle|seller_title)"\s*:\s*"([^"]{2,60})"', html)
    titles = re.findall(r'"(?:title|name)"\s*:\s*"([^"]{15,100})"', html)
    prices = re.findall(r'"(?:finalPrice|price)"\s*:\s*"?(\d{2,7})"?', html)

    return {
        "items": items[:20],
        "regex_sellers": list(dict.fromkeys(sellers))[:15],
        "regex_titles": titles[:10],
        "regex_prices": [int(x) for x in prices[:15]],
        "html_len": len(html),
    }


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel="chrome")
        context = await browser.new_context(
            locale="ru-RU",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
            viewport={"width": 1400, "height": 1000},
        )
        page = await context.new_page()
        await page.goto("https://www.ozon.ru/", wait_until="domcontentloaded", timeout=50000)
        await page.wait_for_timeout(2500)

        results = {}
        for item in top:
            q = (item.get("name") or item["offer_id"])[:55]
            r = await scrape_search(page, q)
            results[item["offer_id"]] = {"query": q, **r}
            print(f"\n=== {item['offer_id']} === {q[:40]}")
            print("  html", r.get("html_len"), "items", len(r.get("items") or []), "sellers", r.get("regex_sellers"))
            for it in (r.get("items") or [])[:6]:
                print("  ", it.get("price"), (it.get("name") or "")[:50], "seller=", it.get("seller"))
            await page.wait_for_timeout(1200)

        json.dump(results, open(OUT / "competitors_dom.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        await page.screenshot(path=str(OUT / "ozon_search_sample.png"))
        await browser.close()
        print("\nDONE")


if __name__ == "__main__":
    asyncio.run(main())
