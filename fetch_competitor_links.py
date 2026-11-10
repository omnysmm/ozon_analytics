"""Resolve cheapest competing Ozon offer per SKU via storefront search (headed Edge, crash-resilient)."""
import json
import re
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(r"C:\Users\Alex\ozon_analytics")
PROF = OUT / ".edge_profile"
RES = OUT / "competitor_links.json"
TOP_N = 200

vs = json.load(open(OUT / "vsmarket.json", encoding="utf-8"))
rows = sorted(vs["rows"], key=lambda r: -(r.get("oct_rev") or 0))[:TOP_N]
our_pids = {str(p["product_id"]) for p in json.load(open(OUT / "price_indexes_fresh.json", encoding="utf-8"))}

EXTRACT = """() => {
    const out = [];
    const anchors = Array.from(document.querySelectorAll('a[href*="/product/"]'));
    const seen = new Set();
    for (const a of anchors) {
        const href = a.getAttribute('href') || '';
        const m = href.match(/\\/product\\/([^/?]+)-(\\d+)\\/?/);
        if (!m) continue;
        const pid = m[2];
        if (seen.has(pid)) continue;
        seen.add(pid);
        let tile = a.closest('.tile-root') || a.closest('[data-index]');
        if (!tile) {
            let node = a.parentElement, best = null;
            for (let i = 0; i < 10 && node; i++) {
                const t = node.innerText || '';
                if (t.includes('₽') && t.length < 800) best = node;
                node = node.parentElement;
            }
            tile = best || a.parentElement;
        }
        const text = (tile && tile.innerText) ? tile.innerText.trim() : (a.innerText || '').trim();
        out.push({pid, href, text: text.slice(0, 400)});
    }
    return out;
}"""


def parse_tile(t):
    text = t.get("text") or ""
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    prices = []
    for ln in lines:
        for m in re.finditer(r"(\d[\d\s]{0,9}\d|\d)\s*₽", ln):
            try:
                prices.append(int(m.group(1).replace(" ", "")))
            except Exception:
                pass
    name = ""
    for ln in lines:
        if "₽" in ln or re.match(r"^[-−]?\d{1,3}%$", ln) or re.search(r"отзыв|ед осталось|^\d+[.,]\d+$", ln, re.I):
            continue
        if len(ln) >= 8:
            name = ln[:140]
            break
    seller = ""
    for ln in lines:
        if re.search(r"продав|ООО|ИП |ЗАО|Co\.,|Ltd|store", ln, re.I) and len(ln) < 80:
            seller = ln
            break
    return {"product_id": t["pid"], "href": t["href"], "name": name, "price": prices[0] if prices else None,
            "seller": seller, "all_prices": prices[:4]}


def load():
    if RES.exists():
        try:
            return json.load(open(RES, encoding="utf-8"))
        except Exception:
            pass
    return {}


def main():
    results = load()
    todo = [r for r in rows if not (results.get(r["offer_id"], {}) or {}).get("comp")]
    print("to resolve:", len(todo), "of", len(rows), flush=True)

    with sync_playwright() as p:
        ctx = None
        page = None
        idx = 0
        while idx < len(todo):
            if page is None:
                try:
                    ctx = p.chromium.launch_persistent_context(
                        str(PROF), channel="msedge", headless=False,
                        viewport={"width": 1440, "height": 1100}, locale="ru-RU",
                        timezone_id="Europe/Moscow",
                        args=["--disable-blink-features=AutomationControlled", "--no-first-run", "--no-default-browser-check"],
                    )
                    page = ctx.pages[0] if ctx.pages else ctx.new_page()
                    page.goto("https://www.ozon.ru", wait_until="domcontentloaded", timeout=70000)
                    page.wait_for_timeout(4000)
                except Exception as e:
                    print("launch fail", str(e)[:100], flush=True)
                    time.sleep(3)
                    continue
            q = todo[idx]
            idx += 1
            name = (q.get("name") or "").strip()[:80]
            if not name:
                results[q["offer_id"]] = {"offer_id": q["offer_id"], "error": "no name"}
                continue
            url = "https://www.ozon.ru/search/?text=" + name + "&sorting=price"
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(4500)
                page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.5)")
                page.wait_for_timeout(1000)
                tiles = page.evaluate(EXTRACT)
                parsed = [parse_tile(t) for t in tiles]
                others = [t for t in parsed if str(t["product_id"]) not in our_pids and t.get("price")]
                others.sort(key=lambda t: t["price"])
                best = others[0] if others else None
                results[q["offer_id"]] = {
                    "offer_id": q["offer_id"], "query": name, "our_price": q.get("our_price"),
                    "n_found": len(parsed), "n_others": len(others), "comp": best,
                    "candidates": others[:5],
                }
                print(f"[{idx}/{len(todo)}] {q['offer_id'][:18]:18s} ours={q.get('our_price')} "
                      f"found={len(parsed)} others={len(others)} best={best['price'] if best else '-'}", flush=True)
                if idx % 10 == 0:
                    json.dump(results, open(RES, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            except Exception as e:
                print(f"[{idx}/{len(todo)}] {q['offer_id']} ERR {str(e)[:90]}", flush=True)
                results[q["offer_id"]] = results.get(q["offer_id"]) or {"offer_id": q["offer_id"], "error": str(e)[:160]}
                try:
                    page.close()
                    ctx.close()
                except Exception:
                    pass
                page = None
                time.sleep(2)
        try:
            if ctx:
                ctx.close()
        except Exception:
            pass

    json.dump(results, open(RES, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    ok = sum(1 for v in results.values() if v.get("comp"))
    print("saved entries", len(results), "with competitor:", ok)


if __name__ == "__main__":
    main()
