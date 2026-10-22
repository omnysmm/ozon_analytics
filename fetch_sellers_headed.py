"""Aggressive fetch of competitor SELLER names from Ozon (read-only)."""
import asyncio
import json
import re
from pathlib import Path
from urllib.parse import quote

from playwright.async_api import async_playwright

OUT = Path(r"C:\Users\Alex\ozon_analytics")
econ = json.load(open(OUT / "sku_economics.json", encoding="utf-8"))
top = sorted(econ, key=lambda r: -(r.get("qty_sold") or 0))[:12]


async def main():
    async with async_playwright() as p:
        # headed Chrome often passes Ozon anti-bot better than headless
        browser = await p.chromium.launch(
            headless=False,
            channel="chrome",
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
                "--no-default-browser-check",
            ],
        )
        context = await browser.new_context(
            locale="ru-RU",
            timezone_id="Europe/Moscow",
            viewport={"width": 1366, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
        )
        await context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
        )
        page = await context.new_page()
        await page.goto("https://www.ozon.ru/", wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(4000)
        html0 = await page.content()
        print("home html", len(html0), "title", await page.title())
        await page.screenshot(path=str(OUT / "ozon_home.png"))

        results = {}
        for item in top:
            q = (item.get("name") or item["offer_id"])[:55]
            url = f"https://www.ozon.ru/search/?text={quote(q)}&from_global=true"
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=50000)
                await page.wait_for_timeout(5000)
                await page.mouse.wheel(0, 800)
                await page.wait_for_timeout(2000)
            except Exception as e:
                results[item["offer_id"]] = {"error": str(e)}
                print("NAV ERR", item["offer_id"], e)
                continue

            html = await page.content()
            # seller-like patterns in ozon search JSON/DOM
            sellers = re.findall(
                r'"(?:sellerName|seller_name|sellerTitle|seller_title|brandName|brand_title|brandTitle)"\s*:\s*"([^"]{2,60})"',
                html,
            )
            # DOM: buttons/links near "Продавец"
            dom_sellers = await page.evaluate(
                """() => {
                  const out = [];
                  const walk = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
                  let n;
                  while ((n = walk.nextNode())) {
                    const t = (n.textContent||'').trim();
                    if (/^Продавец$/i.test(t) || /^Продавец:/i.test(t)) {
                      const el = n.parentElement;
                      const parent = el && el.parentElement;
                      const sib = el && (el.nextElementSibling || parent && parent.nextElementSibling);
                      if (sib) out.push((sib.innerText||sib.textContent||'').trim().slice(0,80));
                      if (parent) out.push((parent.innerText||'').trim().slice(0,120));
                    }
                  }
                  return out.slice(0, 20);
                }"""
            )
            # product tiles with seller line
            tiles = await page.evaluate(
                """() => {
                  const out = [];
                  document.querySelectorAll('a[href*="/product/"]').forEach((a, i) => {
                    if (i > 25) return;
                    const box = a.closest('div') || a;
                    const txt = (box.innerText||'').split('\\n').map(s=>s.trim()).filter(Boolean);
                    out.push({href: a.getAttribute('href'), lines: txt.slice(0, 12)});
                  });
                  return out;
                }"""
            )

            uniq = list(dict.fromkeys(sellers))
            results[item["offer_id"]] = {
                "query": q,
                "html_len": len(html),
                "sellers_json": uniq[:15],
                "sellers_dom": dom_sellers[:10],
                "tiles": tiles[:8],
            }
            print(
                f"{item['offer_id']:16s} html={len(html)} json_sellers={uniq[:5]} dom={dom_sellers[:3]}"
            )
            await page.wait_for_timeout(1500)
            if item["offer_id"] == top[0]["offer_id"]:
                await page.screenshot(path=str(OUT / "ozon_search1.png"), full_page=False)

        json.dump(results, open(OUT / "competitors_sellers2.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        await browser.close()
        print("DONE")


if __name__ == "__main__":
    asyncio.run(main())
