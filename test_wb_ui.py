from pathlib import Path
from playwright.sync_api import sync_playwright

url = Path(r"C:\Users\Alex\ozon_analytics\index.html").resolve().as_uri()
with sync_playwright() as p:
    b = p.chromium.launch()
    page = b.new_page(viewport={"width": 1500, "height": 950})
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.goto(url, wait_until="load")
    page.wait_for_timeout(900)

    # WB analytics tab
    page.click('button[data-tab="wbsku"]')
    page.wait_for_timeout(500)
    wb_rows = page.evaluate("document.querySelectorAll('#wbTable tbody tr').length")
    wb_count = page.inner_text("#wbCount")
    wb_cards = page.inner_text("#wbCards")
    print("WB tab", wb_rows, wb_count, "cards", wb_cards)

    # filter
    page.fill("#wbSearch", "KM5415")
    page.wait_for_timeout(250)
    wb_f = page.evaluate("document.querySelectorAll('#wbTable tbody tr').length")
    page.click("#wbReset")
    page.wait_for_timeout(200)
    wb_b = page.evaluate("document.querySelectorAll('#wbTable tbody tr').length")
    print("WB filter", wb_f, "reset", wb_b)

    # comparison tab
    page.click('button[data-tab="wb"]')
    page.wait_for_timeout(600)
    cmp_rows = page.evaluate("document.querySelectorAll('#cmpBody tr').length")
    cmp_sku = page.evaluate("document.querySelectorAll('#cmpSkuTable tbody tr').length")
    print("cmp metrics", cmp_rows, "cmp skus", cmp_sku)
    print("cmp sample", page.evaluate("document.querySelector('#cmpBody tr') && document.querySelector('#cmpBody tr').innerText"))

    # xlsx export wb
    with page.expect_download() as di:
        page.click('button[data-tab="wbsku"]')
        page.wait_for_timeout(200)
        page.click('button[data-xls="wb"]')
    d = di.value
    print("xlsx", d.suggested_filename)
    assert d.suggested_filename.endswith(".xlsx")

    print("errs", errs)
    ok = wb_rows == 10 and cmp_rows >= 5 and cmp_sku > 0 and not errs and d.suggested_filename.endswith(".xlsx")
    print("WB_UI_OK" if ok else "WB_UI_FAIL")
    b.close()
