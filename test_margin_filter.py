from pathlib import Path
from playwright.sync_api import sync_playwright

url = Path(r"C:\Users\Alex\ozon_analytics\index.html").resolve().as_uri()
with sync_playwright() as p:
    b = p.chromium.launch()
    page = b.new_page()
    page.goto(url, wait_until="load")
    page.wait_for_timeout(600)
    page.click('button[data-tab="prices"]')
    page.wait_for_timeout(300)
    total = page.evaluate("document.querySelectorAll('#recTable tbody tr').length")
    page.select_option("#rMargin", "neg")
    page.wait_for_timeout(250)
    neg = page.evaluate("document.querySelectorAll('#recTable tbody tr').length")
    page.select_option("#rMargin", "ok")
    page.wait_for_timeout(250)
    ok = page.evaluate("document.querySelectorAll('#recTable tbody tr').length")
    page.select_option("#rMargin", "low")
    page.wait_for_timeout(250)
    low = page.evaluate("document.querySelectorAll('#recTable tbody tr').length")
    page.select_option("#rMargin", "")
    page.wait_for_timeout(250)
    back = page.evaluate("document.querySelectorAll('#recTable tbody tr').length")
    has = page.evaluate("!!document.getElementById('rMargin')")
    print("has_filter", has, "total", total, "neg", neg, "low", low, "ok", ok, "back", back)
    # display cap is 150 rows; filtering works if categories change counts and reset restores
    ok_flag = (
        has
        and back == total
        and neg < total
        and (neg > 0 or low > 0)
        and ok >= neg  # profitable bucket exists
    )
    print("MARGIN_FILTER_OK" if ok_flag else "MARGIN_FILTER_FAIL")
    b.close()
