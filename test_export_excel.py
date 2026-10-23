"""Export Excel (.xlsx) from each table with filters applied; validate OOXML/ZIP."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import re
import zipfile

URL = Path(r"C:\Users\Alex\ozon_analytics\index.html").resolve().as_uri()
OUT = Path(r"C:\Users\Alex\ozon_analytics\_xls_test")


def count_sheet_rows(zpath: Path) -> int:
    with zipfile.ZipFile(zpath) as z:
        names = z.namelist()
        assert "xl/worksheets/sheet1.xml" in names, names
        assert "xl/workbook.xml" in names
        xml = z.read("xl/worksheets/sheet1.xml").decode("utf-8", "replace")
    return len(re.findall(r"<row[ >]", xml))


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
    full = page.evaluate("EXPORT_STATE.sku.length")
    with page.expect_download() as di:
        page.click('button[data-xls="sku"]')
    d = di.value
    assert d.suggested_filename.endswith(".xlsx"), d.suggested_filename
    path = OUT / d.suggested_filename
    d.save_as(path)
    raw = path.read_bytes()[:4]
    assert raw == b"PK\x03\x04", raw
    n = count_sheet_rows(path)
    print("SKU filter dom", filtered, "EXPORT_STATE", full, "xml_rows_incl_header", n, "file", path.name)
    assert n == full + 1, (n, full)
    with zipfile.ZipFile(path) as z:
        sheet = z.read("xl/worksheets/sheet1.xml").decode("utf-8", "replace")
    assert "Насадк" in sheet or "NK54" in sheet

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
    assert d2.suggested_filename.endswith(".xlsx")
    with zipfile.ZipFile(p2) as z:
        sheet2 = z.read("xl/worksheets/sheet1.xml").decode("utf-8", "replace")
    hdr = re.search(r'<row r="1">(.*?)</row>', sheet2).group(1)
    print("SKU after hide qty header:", hdr[:220])
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
    n3 = count_sheet_rows(p3)
    print("REC neg rows", full_rec, "xml", n3, p3.name)
    assert p3.name.endswith(".xlsx")
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
    n4 = count_sheet_rows(p4)
    print("COST neg rows", full_cost, "xml", n4, p4.name)
    assert p4.name.endswith(".xlsx")
    assert n4 == full_cost + 1

    # --- FEES ---
    page.click('button[data-tab="fees"]')
    page.wait_for_timeout(250)
    with page.expect_download() as di5:
        page.click('button[data-xls="fee"]')
    d5 = di5.value
    p5 = OUT / d5.suggested_filename
    d5.save_as(p5)
    n5 = count_sheet_rows(p5)
    print("FEE rows", n5, p5.name)
    assert p5.name.endswith(".xlsx")
    assert n5 > 1
    with zipfile.ZipFile(p5) as z:
        assert "Комиссия" in z.read("xl/worksheets/sheet1.xml").decode("utf-8", "replace")

    print("page errors", errs)
    assert not errs
    print("EXPORT_OK")
    b.close()
