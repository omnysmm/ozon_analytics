"""Export Excel from each table with filters applied; validate SpreadsheetML."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import re

URL = Path(r"C:\Users\Alex\ozon_analytics\index.html").resolve().as_uri()
OUT = Path(r"C:\Users\Alex\ozon_analytics\_xls_test")


def count_rows_xml(xml: str) -> int:
    return len(re.findall(r"<Row>", xml))


with sync_playwright() as p:
    b = p.chromium.launch()
    page = b.new_page()
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.goto(URL, wait_until="load")
    page.wait_for_timeout(700)
    OUT.mkdir(exist_ok=True)

    # --- SKU with filter ---
    page.click('button[data-tab="sku"]')
    page.wait_for_timeout(250)
    page.fill("#fSearch", "NK54")
    page.wait_for_timeout(250)
    filtered = page.evaluate("document.querySelectorAll('#skuTable tbody tr').length")
    # export uses full filtered set, not the DOM cap
    full = page.evaluate("EXPORT_STATE.sku.length")
    with page.expect_download() as di:
        page.click('button[data-xls="sku"]')
    d = di.value
    path = OUT / d.suggested_filename
    d.save_as(path)
    xml = path.read_text(encoding="utf-8", errors="replace")
    n = count_rows_xml(xml)
    print("SKU filter dom", filtered, "EXPORT_STATE", full, "xml_rows_incl_header", n, "file", path.name)
    assert "Насадк" in xml or "NK54" in xml
    assert n == full + 1, (n, full)

    # clear search, hide a column, export again
    page.fill("#fSearch", "")
    page.wait_for_timeout(200)
    page.click('[data-toggle="colMenuSku"]')
    page.wait_for_timeout(150)
    page.evaluate("""() => {
      const labels = [...document.querySelectorAll('#colMenuSku label')];
      labels[2].querySelector('input').click(); // hide qty
    }""")
    page.wait_for_timeout(150)
    page.keyboard.press("Escape")
    with page.expect_download() as di2:
        page.click('button[data-xls="sku"]')
    d2 = di2.value
    p2 = OUT / d2.suggested_filename
    d2.save_as(p2)
    xml2 = p2.read_text(encoding="utf-8", errors="replace")
    hdr = re.search(r"<Row>(.*?)</Row>", xml2).group(1)
    print("SKU after hide qty header:", hdr[:200])
    assert "Кол-во" not in hdr

    # --- PRICES with margin filter ---
    page.click('button[data-tab="prices"]')
    page.wait_for_timeout(250)
    page.select_option("#rMargin", "neg")
    page.wait_for_timeout(250)
    full_rec = page.evaluate("EXPORT_STATE.rec.length")
    with page.expect_download() as di3:
        page.click('button[data-xls="rec"]')
    d3 = di3.value
    p3 = OUT / d3.suggested_filename
    d3.save_as(p3)
    xml3 = p3.read_text(encoding="utf-8", errors="replace")
    n3 = count_rows_xml(xml3)
    print("REC neg rows", full_rec, "xml", n3, p3.name)
    assert n3 == full_rec + 1
    assert full_rec > 0

    # --- COSTS ---
    page.click('button[data-tab="costs"]')
    page.wait_for_timeout(250)
    page.select_option("#cMargin", "neg")
    page.wait_for_timeout(250)
    full_cost = page.evaluate("EXPORT_STATE.cost.length")
    with page.expect_download() as di4:
        page.click('button[data-xls="cost"]')
    d4 = di4.value
    p4 = OUT / d4.suggested_filename
    d4.save_as(p4)
    xml4 = p4.read_text(encoding="utf-8", errors="replace")
    n4 = count_rows_xml(xml4)
    print("COST neg rows", full_cost, "xml", n4, p4.name)
    assert n4 == full_cost + 1

    # --- FEES ---
    page.click('button[data-tab="fees"]')
    page.wait_for_timeout(250)
    with page.expect_download() as di5:
        page.click('button[data-xls="fee"]')
    d5 = di5.value
    p5 = OUT / d5.suggested_filename
    d5.save_as(p5)
    xml5 = p5.read_text(encoding="utf-8", errors="replace")
    n5 = count_rows_xml(xml5)
    print("FEE rows", n5, p5.name)
    assert n5 > 1
    assert "Комиссия" in xml5

    print("page errors", errs)
    assert not errs
    print("EXPORT_OK")
    b.close()
