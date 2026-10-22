"""Reuse working Edge persistent profile; save product HTML and mine seller fields."""
import json
import re
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path(r"C:\Users\Alex\ozon_analytics")
PROF = OUT / ".edge_profile"
PIDS = {"NK5415": 255832676, "NK54125": 306414751, "I-D-P": 1424446737, "NL24": 306414721}


def mine(html: str):
    keys = re.findall(r'"([A-Za-z_][A-Za-z0-9_]{2,40})"\s*:', html)
    interesting = [k for k in dict.fromkeys(keys) if re.search(
        r"sell|brand|compa|merchant|vendor|shop|store|company|trade|manufact", k, re.I)]
    pats = [
        r'"sellerName"\s*:\s*"([^"]{2,80})"',
        r'"seller_name"\s*:\s*"([^"]{2,80})"',
        r'"brandName"\s*:\s*"([^"]{2,80})"',
        r'"brand_name"\s*:\s*"([^"]{2,80})"',
        r'"tradeMark"\s*:\s*"([^"]{2,80})"',
        r'"companyName"\s*:\s*"([^"]{2,80})"',
        r'"sellerTitle"\s*:\s*"([^"]{2,80})"',
        r'"author"\s*:\s*"([^"]{2,80})"',
    ]
    sellers = []
    for p in pats:
        sellers.extend(re.findall(p, html))
    # JSON-LD
    ld = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
    ld_sellers = []
    for block in ld:
        ld_sellers.extend(re.findall(r'"(?:seller|brand|manufacturer)"\s*:\s*\{[^}]{0,200}?"name"\s*:\s*"([^"]+)"', block))
        ld_sellers.extend(re.findall(r'"name"\s*:\s*"([^"]+)"\s*,\s*"@type"\s*:\s*"(?:Organization|Brand|Store)"', block))
    return {
        "interesting_keys": interesting[:60],
        "sellers": list(dict.fromkeys(sellers))[:20],
        "ld_sellers": list(dict.fromkeys(ld_sellers))[:20],
        "html_len": len(html),
    }


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
            args=["--disable-blink-features=AutomationControlled", "--no-first-run", "--no-default-browser-check"],
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto("https://www.ozon.ru/", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)
        print("home", page.title(), len(page.content()))

        for offer, pid in PIDS.items():
            try:
                page.goto(f"https://www.ozon.ru/product/{pid}/", wait_until="domcontentloaded", timeout=70000)
                page.wait_for_timeout(8000)
                html = page.content()
                entry = mine(html)
                entry["title"] = page.title()
                entry["url"] = page.url
                # visible seller-ish lines
                try:
                    entry["visible"] = page.evaluate("""() => {
                      const t = document.body.innerText || '';
                      return t.split('\\n').map(s=>s.trim()).filter(s =>
                        /продав|бренд|изготов|реализу|компани|ООО|ИП |ЗАО|АО /i.test(s) && s.length < 100
                      ).slice(0, 25);
                    }""")
                except Exception as e:
                    entry["visible_err"] = str(e)
                # in-page composer
                try:
                    comp = page.evaluate("""async (pid) => {
                      try {
                        const r = await fetch(`/api/composer-api.bx/page/json/v2?url=/product/${pid}/`, {credentials:'include'});
                        const t = await r.text();
                        return {status:r.status, len:t.length, sample:t.slice(0, 120000)};
                      } catch(e) { return {error: String(e)}; }
                    }""", pid)
                    entry["composer"] = {
                        "status": comp.get("status"),
                        "len": comp.get("len"),
                        "error": comp.get("error"),
                        **({"mined": mine(comp["sample"])} if comp.get("sample") else {}),
                    }
                except Exception as e:
                    entry["composer"] = {"error": str(e)}
                results[offer] = entry
                print(offer, "len", entry["html_len"], "title", entry["title"][:40],
                      "sellers", entry["sellers"], "ld", entry["ld_sellers"],
                      "vis", entry.get("visible"), "comp", (entry.get("composer") or {}).get("mined", {}).get("sellers"))
                if offer == "NK5415":
                    (OUT / "ozon_product_nk5415.html").write_text(html, encoding="utf-8")
                    page.screenshot(path=str(OUT / "ozon_product_nk5415.png"))
            except Exception as e:
                results[offer] = {"error": str(e)}
                print("ERR", offer, e)
        context.close()

    json.dump(results, open(OUT / "competitors_sellers3.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("wrote competitors_sellers3.json")


if __name__ == "__main__":
    main()
