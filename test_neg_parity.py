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

    def neg_offers():
        return page.evaluate("""() => {
          const out = [];
          document.querySelectorAll('tbody tr').forEach(tr => {
            out.push(tr.children[0].innerText.trim());
          });
          return out;
        }""")

    page.click('button[data-tab="prices"]')
    page.wait_for_timeout(200)
    page.select_option("#rMargin", "neg")
    page.wait_for_timeout(250)
    rec_n = page.evaluate("EXPORT_STATE.rec.length")
    rec_ids = page.evaluate("EXPORT_STATE.rec.map(r => r.offer_id).sort()")
    rec_dom = page.evaluate("document.querySelectorAll('#recTable tbody tr').length")

    page.click('button[data-tab="costs"]')
    page.wait_for_timeout(200)
    page.select_option("#cMargin", "neg")
    page.wait_for_timeout(250)
    cost_n = page.evaluate("EXPORT_STATE.cost.length")
    cost_ids = page.evaluate("EXPORT_STATE.cost.map(r => r.offer_id).sort()")
    cost_dom = page.evaluate("document.querySelectorAll('#costTable tbody tr').length")

    print("rec", rec_n, rec_dom, rec_ids)
    print("cost", cost_n, cost_dom, cost_ids)
    print("errs", errs)
    ok = rec_ids == cost_ids and rec_n == cost_n == 5 and rec_n > 0 and not errs
    print("PARITY_OK" if ok else "PARITY_FAIL")
    b.close()
