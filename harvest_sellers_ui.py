"""Human-like Ozon navigation via search UI to harvest seller names."""
import json
import re
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path(r"C:\Users\Alex\ozon_analytics")
PROF = OUT / ".edge_profile"

QUERIES = {
    "NK5415": "Насадки для установки кнопок Альфа 15 мм для Пресса Тер 2",
    "NK54125": "Насадки для установки кнопок Альфа 12,5 мм для пресса Тер 2",
    "I-D-P": "Крючок для поднятия петель игла для трикотажа",
    "NL24": "Насадка пуансон матрица для установки люверсов 10мм на пресс ТЕР-2",
}

PATS = [
    r'"sellerName"\s*:\s*"([^"]{2,80})"',
    r'"seller_name"\s*:\s*"([^"]{2,80})"',
    r'"brandName"\s*:\s*"([^"]{2,80})"',
    r'"brand_name"\s*:\s*"([^"]{2,80})"',
    r'"tradeMark"\s*:\s*"([^"]{2,80})"',
]


def mine(text: str):
    out = []
    for p in PATS:
        out.extend(re.findall(p, text))
    return list(dict.fromkeys(out))[:20]


def main():
    results = {}
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            str(PROF),
            channel="msedge",
            headless=False,
            viewport={"width": 1440, "height": 1100},
            locale="ru-RU",
            timezone_id="Europe/Moscow",
            args=["--disable-blink-features=AutomationControlled", "--no-first-run"],
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto("https://www.ozon.ru/", wait_until="domcontentloaded", timeout=70000)
        page.wait_for_timeout(6000)
        print("home ok", page.title(), len(page.content()))

        for offer, q in QUERIES.items():
            entry = {"query": q}
            try:
                # type into search
                box = page.locator('input[name="search"], input[type="search"], input[placeholder*="Искать"], form input').first
                box.wait_for(state="visible", timeout=15000)
                box.click()
                page.wait_for_timeout(500)
                box.fill("")
                box.type(q, delay=25)
                page.wait_for_timeout(800)
                box.press("Enter")
                page.wait_for_timeout(7000)
                html = page.content()
                entry["search_url"] = page.url
                entry["search_len"] = len(html)
                entry["search_sellers"] = mine(html)
                entry["title"] = page.title()
                print(offer, "search", page.url[:80], len(html), entry["search_sellers"][:6])

                # click first product card link
                link = page.locator('a[href*="/product/"]').first
                if link.count():
                    href = link.get_attribute("href")
                    entry["first_href"] = href
                    link.click()
                    page.wait_for_timeout(8000)
                    html2 = page.content()
                    entry["product_url"] = page.url
                    entry["product_len"] = len(html2)
                    entry["product_sellers"] = mine(html2)
                    try:
                        entry["visible"] = page.evaluate("""() => {
                          const t = document.body.innerText || '';
                          return t.split('\\n').map(s=>s.trim()).filter(s =>
                            /продав|бренд|изготов|реализу|ООО|ИП |ЗАО|АО /i.test(s) && s.length < 110
                          ).slice(0, 20);
                        }""")
                    except Exception:
                        pass
                    # DOM: seller block
                    try:
                        entry["dom_seller"] = page.evaluate("""() => {
                          const out = [];
                          document.querySelectorAll('a,span,div').forEach(el => {
                            const t = (el.innerText||'').trim();
                            if (t && t.length < 60 && /продав/i.test(el.getAttribute('href')||'') ) out.push(t);
                            const href = el.getAttribute && el.getAttribute('href');
                            if (href && /seller|brand|shop/.test(href)) out.push({href, t: t.slice(0,60)});
                          });
                          return out.slice(0, 15);
                        }""")
                    except Exception:
                        pass
                    print("  product", entry["product_url"][:80], entry["product_len"], entry["product_sellers"][:6], "vis", entry.get("visible"))
                    if offer == "NK5415":
                        (OUT / "ozon_search_nk5415.html").write_text(html, encoding="utf-8")
                        (OUT / "ozon_product_nk5415.html").write_text(html2, encoding="utf-8")
                        page.screenshot(path=str(OUT / "ozon_product_nk5415.png"))
                else:
                    entry["no_product_link"] = True
                    print("  no product link")
                    # back home for next
                    page.goto("https://www.ozon.ru/", wait_until="domcontentloaded", timeout=60000)
                    page.wait_for_timeout(4000)
                    continue
                # back home for next query
                page.goto("https://www.ozon.ru/", wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(4000)
            except Exception as e:
                entry["error"] = str(e)
                print("ERR", offer, e)
                try:
                    page.goto("https://www.ozon.ru/", wait_until="domcontentloaded", timeout=60000)
                    page.wait_for_timeout(4000)
                except Exception:
                    pass
            results[offer] = entry

        context.close()

    json.dump(results, open(OUT / "competitors_sellers3.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    named = [o for o, e in results.items() if e.get("product_sellers") or e.get("search_sellers") or e.get("visible")]
    print("with name-like data:", named)
    print("wrote competitors_sellers3.json")


if __name__ == "__main__":
    main()
