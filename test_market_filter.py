from pathlib import Path
from playwright.sync_api import sync_playwright

url = Path(r"C:\Users\Alex\ozon_analytics\index.html").resolve().as_uri()
with sync_playwright() as p:
    b = p.chromium.launch()
    page = b.new_page()
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.goto(url, wait_until="load")
    page.wait_for_timeout(700)

    page.click('button[data-tab="prices"]')
    page.wait_for_timeout(250)
    has = page.evaluate("!!document.getElementById('rMarket')")
    total = page.evaluate("EXPORT_STATE.rec.length")

    counts = {}
    for val in ("cheap", "dear", "not_dear", "no_index"):
        page.select_option("#rMarket", val)
        page.wait_for_timeout(200)
        counts[val] = page.evaluate("EXPORT_STATE.rec.length")
    page.select_option("#rMarket", "")
    page.wait_for_timeout(150)
    back = page.evaluate("EXPORT_STATE.rec.length")

    # combined filters then reset
    page.select_option("#rMarket", "dear")
    page.select_option("#rMargin", "ok")
    page.fill("#rSearch", "NK")
    page.wait_for_timeout(200)
    combo = page.evaluate("EXPORT_STATE.rec.length")
    page.click("#rReset")
    page.wait_for_timeout(200)
    after_reset = page.evaluate("EXPORT_STATE.rec.length")
    cleared = page.evaluate("""() => ({
      q: document.getElementById('rSearch').value,
      a: document.getElementById('rAction').value,
      m: document.getElementById('rMargin').value,
      k: document.getElementById('rMarket').value
    })""")

    # costs reset
    page.click('button[data-tab="costs"]')
    page.wait_for_timeout(200)
    page.select_option("#cMargin", "neg")
    page.fill("#cSearch", "NK")
    page.wait_for_timeout(200)
    page.click("#cReset")
    page.wait_for_timeout(200)
    cost_cleared = page.evaluate("""() => ({
      q: document.getElementById('cSearch').value,
      m: document.getElementById('cMargin').value,
      n: EXPORT_STATE.cost.length
    })""")

    # sku reset label
    page.click('button[data-tab="sku"]')
    page.wait_for_timeout(150)
    freset = page.inner_text("#fReset")
    has_r = page.evaluate("!!document.getElementById('rReset')")
    has_c = page.evaluate("!!document.getElementById('cReset')")

    print("has_market", has, "total", total, counts, "back", back)
    print("combo", combo, "after_reset", after_reset, cleared)
    print("cost", cost_cleared, "fReset", freset, "rReset", has_r, "cReset", has_c)
    print("errs", errs)

    ok = (
        has and total > 0
        and counts["no_index"] + counts["cheap"] + counts["dear"] <= total + counts["no_index"]  # overlap ok
        and back == total
        and after_reset == total
        and cleared == {"q": "", "a": "", "m": "", "k": ""}
        and cost_cleared["q"] == "" and cost_cleared["m"] == ""
        and has_r and has_c
        and "Сброс" in freset
        and not errs
    )
    # cheap+dear+no_index should cover rows with/without market
    covered = counts["cheap"] + counts["dear"] + counts["no_index"]
    print("covered", covered, "of", total, "not_dear", counts["not_dear"])
    ok = ok and covered >= total - 2  # allow tiny float edge
    print("MARKET_RESET_OK" if ok else "MARKET_RESET_FAIL")
    b.close()
