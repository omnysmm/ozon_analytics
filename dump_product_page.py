"""Dump one Ozon product page and hunt for seller/brand fields."""
import json
import re
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path(r"C:\Users\Alex\ozon_analytics")
PID = 255832676  # NK5415

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=False, args=["--no-first-run"])
    context = browser.new_context(
        locale="ru-RU",
        timezone_id="Europe/Moscow",
        viewport={"width": 1440, "height": 1100},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
    )
    page = context.new_page()
    page.goto("https://www.ozon.ru/", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(4000)
    page.goto(f"https://www.ozon.ru/product/{PID}/", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(8000)
    html = page.content()
    (OUT / "ozon_product_nk5415.html").write_text(html, encoding="utf-8")
    page.screenshot(path=str(OUT / "ozon_product_nk5415.png"), full_page=False)
    print("saved html", len(html), "title", page.title())

    # Search for interesting JSON keys
    keys = re.findall(r'"([A-Za-z_][A-Za-z0-9_]{2,40})"\s*:', html)
    interesting = [k for k in dict.fromkeys(keys) if re.search(r"sell|brand|compa|merchant|vendor|shop|store|торг|продав", k, re.I)]
    print("interesting keys:", interesting[:80])

    # Any string near "Продавец"
    for m in re.finditer(r".{0,80}Продавец.{0,120}", html):
        s = m.group(0).replace("\n", " ")
        if len(s) > 20:
            print("NEAR:", s[:200])
            break

    # composer widget tree
    try:
        data = page.evaluate("""() => {
          const s = document.querySelector('#__NEXT_DATA__') || document.querySelector('script[type="application/json"]');
          return s ? s.textContent.slice(0, 2000) : null;
        }""")
        print("next_data sample:", (data or "")[:300])
    except Exception as e:
        print("next fail", e)

    # try composer fetch from inside page
    try:
        comp = page.evaluate("""async (pid) => {
          const r = await fetch(`/api/composer-api.bx/page/json/v2?url=/product/${pid}/`, {credentials:'include'});
          const t = await r.text();
          return {status:r.status, len:t.length, text:t.slice(0,8000)};
        }""", PID)
        print("composer", comp["status"], comp["len"])
        (OUT / "composer_nk5415.json").write_text(comp["text"] or "", encoding="utf-8")
        if comp.get("text"):
            sk = re.findall(r'"([A-Za-z_][A-Za-z0-9_]{2,40})"\s*:', comp["text"])
            print("composer keys sample:", list(dict.fromkeys(sk))[:60])
            for m in re.finditer(r'"(?:sellerName|brandName|companyName|seller_name|brand_name|tradeMark|sellerTitle)"\s*:\s*"([^"]*)"', comp["text"]):
                print("FOUND", m.group(0)[:120])
    except Exception as e:
        print("composer err", e)

    # visible text search
    try:
        texts = page.evaluate("""() => {
          const out = [];
          document.querySelectorAll('*').forEach(el => {
            const t = (el.childNodes.length===1 && el.childNodes[0].nodeType===3) ? (el.textContent||'').trim() : '';
            if (t && /продав|бренд|изготов|реализ|компани/i.test(t) && t.length < 120) out.push(t);
          });
          return [...new Set(out)].slice(0, 40);
        }""")
        print("visible hits:", texts)
    except Exception as e:
        print("vis err", e)

    # network: listen to composer responses
    browser.close()
print("done")
