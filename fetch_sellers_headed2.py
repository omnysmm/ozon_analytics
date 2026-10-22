"""Fetch competitor SELLER names from Ozon product pages (read-only, headed Chrome)."""
import json
import re
from pathlib import Path
from urllib.parse import quote

from playwright.sync_api import sync_playwright

OUT = Path(r"C:\Users\Alex\ozon_analytics")
live = json.load(open(OUT / "ozon_live_prices.json", encoding="utf-8"))
econ = json.load(open(OUT / "website_data.json", encoding="utf-8"))["sku_economics"]

# product_id map from live prices
pid_by_offer = {}
for key, v in live.items():
    if isinstance(v, dict) and v.get("offer_id") and v.get("product_id"):
        pid_by_offer[v["offer_id"]] = {
            "product_id": v["product_id"],
            "name": v.get("name") or "",
            "price_ozon": v.get("price_ozon"),
        }

top = sorted(econ, key=lambda r: -(r.get("qty_sold") or 0))[:10]
targets = []
for row in top:
    offer = row["offer_id"]
    meta = pid_by_offer.get(offer)
    if not meta:
        # fallback: search live keys
        for k, v in live.items():
            if isinstance(v, dict) and v.get("offer_id") == offer:
                meta = {"product_id": v.get("product_id"), "name": v.get("name") or row.get("name") or ""}
                break
    if meta and meta.get("product_id"):
        targets.append({
            "offer_id": offer,
            "product_id": meta["product_id"],
            "name": meta.get("name") or row.get("name") or "",
            "price_ozon": row.get("price_ozon"),
            "competitor_price": row.get("competitor_price"),
            "competitor_source": row.get("competitor_source"),
        })

print("targets:", [(t["offer_id"], t["product_id"]) for t in targets])

SELLER_PATTERNS = [
    r'"sellerName"\s*:\s*"([^"]{2,80})"',
    r'"seller_name"\s*:\s*"([^"]{2,80})"',
    r'"brandName"\s*:\s*"([^"]{2,80})"',
    r'"brand_name"\s*:\s*"([^"]{2,80})"',
    r'"sellerTitle"\s*:\s*"([^"]{2,80})"',
    r'"companyName"\s*:\s*"([^"]{2,80})"',
]


def extract_sellers(html: str):
    found = []
    for pat in SELLER_PATTERNS:
        found.extend(re.findall(pat, html))
    # unique preserve order
    return list(dict.fromkeys(found))[:15]


def main():
    results = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            channel="chrome",
            args=["--disable-blink-features=AutomationControlled", "--no-first-run"],
        )
        context = browser.new_context(
            locale="ru-RU",
            timezone_id="Europe/Moscow",
            viewport={"width": 1440, "height": 1000},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
            ),
        )
        context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
        )
        page = context.new_page()

        # warm up
        page.goto("https://www.ozon.ru/", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)
        print("home title:", page.title(), "len", len(page.content()))

        for t in targets:
            offer = t["offer_id"]
            pid = t["product_id"]
            url = f"https://www.ozon.ru/product/{pid}/"
            entry = dict(t)
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(6000)
                # try to open "other sellers" / seller block
                try:
                    page.mouse.wheel(0, 600)
                    page.wait_for_timeout(1500)
                except Exception:
                    pass
                html = page.content()
                entry["html_len"] = len(html)
                entry["title"] = page.title()
                entry["sellers"] = extract_sellers(html)

                # DOM scrape for "Продавец" label neighbors
                dom = page.evaluate(
                    """() => {
                      const out = {sellers: [], texts: []};
                      const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
                      let n;
                      while ((n = walker.nextNode())) {
                        const t = (n.textContent || '').trim();
                        if (!t) continue;
                        if (/продавец/i.test(t) && t.length < 40) {
                          const el = n.parentElement;
                          const box = el && el.closest('div,span,li');
                          if (box) out.texts.push(box.innerText.trim().slice(0, 120));
                          const next = el && (el.nextElementSibling || (el.parentElement && el.parentElement.nextElementSibling));
                          if (next) out.sellers.push((next.innerText || '').trim().slice(0, 80));
                        }
                      }
                      return {sellers: out.sellers.slice(0, 12), texts: out.texts.slice(0, 12)};
                    }"""
                )
                entry["dom"] = dom

                # composer json endpoint (often embeds seller)
                try:
                    resp = page.evaluate(
                        """async (pid) => {
                          const r = await fetch(`/api/composer-api.bx/page/json/v2?url=/product/${pid}/`, {
                            credentials: 'include', headers: {'x-o3-app-name': 'dweb_client'}
                          });
                          const t = await r.text();
                          return {status: r.status, len: t.length, sample: t.slice(0, 50000)};
                        }""",
                        pid,
                    )
                    entry["composer_status"] = resp.get("status")
                    entry["composer_len"] = resp.get("len")
                    if resp.get("sample"):
                        entry["composer_sellers"] = extract_sellers(resp["sample"])
                except Exception as e:
                    entry["composer_error"] = str(e)

                # screenshot first success
                if offer == targets[0]["offer_id"]:
                    page.screenshot(path=str(OUT / "ozon_product_sample.png"), full_page=False)

                print(offer, "html", entry["html_len"], "sellers", entry.get("sellers"), "dom", dom.get("sellers"), "composer", entry.get("composer_sellers"))
            except Exception as e:
                entry["error"] = str(e)
                print("ERR", offer, e)
            results[offer] = entry

        browser.close()

    out_path = OUT / "competitors_sellers3.json"
    json.dump(results, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("wrote", out_path)
    named = sum(1 for v in results.values() if v.get("sellers") or (v.get("dom") or {}).get("sellers") or v.get("composer_sellers"))
    print(f"NAMED={named}/{len(results)}")


if __name__ == "__main__":
    main()
