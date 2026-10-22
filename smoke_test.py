"""Smoke-test dashboard: tabs, filters, charts, period."""
import asyncio
from pathlib import Path

from playwright.async_api import async_playwright

HTML = Path(r"C:\Users\Alex\ozon_analytics\index.html").resolve()
OUT = Path(r"C:\Users\Alex\ozon_analytics")


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel="chrome")
        page = await browser.new_page(viewport={"width": 1500, "height": 950})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}") if m.type == "error" else None)

        await page.goto(HTML.as_uri(), wait_until="load", timeout=60000)
        await page.wait_for_timeout(1500)

        # Chart loaded?
        has_chart = await page.evaluate("typeof Chart !== 'undefined'")
        print("Chart.js loaded:", has_chart)

        # canvases painted?
        canvases = await page.evaluate("""() => {
          return Array.from(document.querySelectorAll('canvas')).map(c => ({
            id: c.id, w: c.width, h: c.height
          }));
        }""")
        print("canvases:", canvases)

        # tab click
        await page.click('button[data-tab="sku"]')
        await page.wait_for_timeout(400)
        sku_active = await page.evaluate("document.getElementById('sec-sku').classList.contains('active')")
        print("SKU tab active:", sku_active)

        # table rows
        rows = await page.evaluate("document.querySelectorAll('#skuTable tbody tr').length")
        print("sku rows:", rows)

        # new columns present + populated
        headers = await page.evaluate(
            "[...document.querySelectorAll('#skuTable thead th')].map(th => th.innerText.trim())"
        )
        print("sku headers:", headers)
        has_ozon_unit = any("затраты озон на шт" in h.lower() for h in headers)
        has_rec_price = any("рекомендованная цена" in h.lower() for h in headers)
        new_cols = await page.evaluate("""() => {
          const ths = [...document.querySelectorAll('#skuTable thead th')];
          const iUnit = ths.findIndex(th => th.innerText.toLowerCase().includes('затраты озон на шт'));
          const iRec = ths.findIndex(th => th.innerText.toLowerCase().includes('рекомендованная цена'));
          const tr = document.querySelector('#skuTable tbody tr');
          if (!tr || iUnit < 0 || iRec < 0) return {iUnit, iRec, unit: null, rec: null};
          return {
            iUnit, iRec,
            unit: (tr.children[iUnit] && tr.children[iUnit].innerText || '').trim(),
            rec: (tr.children[iRec] && tr.children[iRec].innerText || '').trim(),
            offer: tr.children[0].innerText.trim()
          };
        }""")
        print("new cols:", has_ozon_unit, has_rec_price, new_cols)

        # search filter
        await page.fill("#fSearch", "NK5415")
        await page.wait_for_timeout(300)
        rows2 = await page.evaluate("document.querySelectorAll('#skuTable tbody tr').length")
        print("after search NK5415 rows:", rows2)
        count_txt = await page.inner_text("#skuCount")
        print("skuCount:", count_txt)

        # action filter (clear search first)
        await page.fill("#fSearch", "")
        await page.select_option("#fAction", "СНИЗИТЬ")
        await page.wait_for_timeout(300)
        rows3 = await page.evaluate("document.querySelectorAll('#skuTable tbody tr').length")
        print("after action СНИЗИТЬ rows:", rows3)

        # reset
        await page.click("#fReset")
        await page.wait_for_timeout(300)
        rows4 = await page.evaluate("document.querySelectorAll('#skuTable tbody tr').length")
        print("after reset rows:", rows4)

        # period
        await page.click('button[data-tab="overview"]')
        await page.fill("#dFrom", "2026-10-01")
        await page.fill("#dTo", "2026-10-14")
        await page.click("#btnPeriod")
        await page.wait_for_timeout(500)
        qty = await page.inner_text("#kQty")
        print("period qty:", qty)

        # fees tab
        await page.click('button[data-tab="fees"]')
        await page.wait_for_timeout(500)
        fee_rows = await page.evaluate("document.querySelectorAll('#feeTable tr').length")
        pf = await page.evaluate("()=>{const c=document.getElementById('chartPlanFact'); return {w:c.width,h:c.height};}")
        print("fee rows:", fee_rows, "planFact canvas:", pf)

        # costs tab
        await page.click('button[data-tab="costs"]')
        await page.wait_for_timeout(300)
        cost_rows = await page.evaluate("document.querySelectorAll('#costTable tbody tr').length")
        print("cost rows:", cost_rows)

        # recs / prices tab
        await page.click('button[data-tab="prices"]')
        await page.wait_for_timeout(500)
        rec_rows = await page.evaluate("document.querySelectorAll('#recTable tbody tr').length")
        idx = await page.evaluate("()=>{const c=document.getElementById('chartIndex'); return {w:c.width,h:c.height};}")
        # price consistency: same offer_id must have same price on both tabs
        rec_data = await page.evaluate("""() => {
          const tr = document.querySelector('#recTable tbody tr');
          if(!tr) return null;
          return {
            offer: tr.children[0].innerText.trim(),
            price: tr.children[2].innerText.trim(),
            comp: tr.children[5].innerText.trim(),
            seller: tr.children[6].innerText.trim()
          };
        }""")
        await page.click('button[data-tab="sku"]')
        await page.wait_for_timeout(300)
        sku_data = await page.evaluate("""() => {
          const rows = Array.from(document.querySelectorAll('#skuTable tbody tr'));
          const target = window.__recOffer || null;
          // find by offer text
          for (const tr of rows) {
            const offer = tr.children[0].innerText.trim();
            if (!target || offer === target) {
              return {
                offer,
                price: tr.children[3].innerText.trim(),
                comp: tr.children[4].innerText.trim(),
                seller: tr.children[5].innerText.trim()
              };
            }
          }
          return rows[0] ? {
            offer: rows[0].children[0].innerText.trim(),
            price: rows[0].children[3].innerText.trim(),
            comp: rows[0].children[4].innerText.trim(),
            seller: rows[0].children[5].innerText.trim()
          } : null;
        }""")
        # evaluate again with offer filter
        if rec_data:
            sku_match = await page.evaluate("""(offer) => {
              const rows = Array.from(document.querySelectorAll('#skuTable tbody tr'));
              for (const tr of rows) {
                if (tr.children[0].innerText.trim() === offer) {
                  return {
                    offer,
                    price: tr.children[3].innerText.trim(),
                    comp: tr.children[4].innerText.trim(),
                    seller: tr.children[5].innerText.trim()
                  };
                }
              }
              return null;
            }""", rec_data["offer"])
        else:
            sku_match = sku_data
        print("recs row:", rec_data)
        print("sku match:", sku_match)
        rec_price = (rec_data or {}).get("price", "")
        sku_price = (sku_match or {}).get("price", "")
        comp_seller = (sku_match or {}).get("seller", "") or (rec_data or {}).get("seller", "")
        print("rec rows:", rec_rows, "index canvas:", idx)

        # wb tab
        await page.click('button[data-tab="wb"]')
        await page.wait_for_timeout(500)
        wb = await page.evaluate("()=>{const c=document.getElementById('chartWbCompare'); return {w:c.width,h:c.height};}")
        print("wb canvas:", wb)

        # js error box
        err_vis = await page.evaluate("document.getElementById('jsError').style.display")
        err_txt = await page.inner_text("#jsError")
        print("jsError visible:", err_vis, "text:", err_txt[:200])

        await page.screenshot(path=str(OUT / "dashboard_check.png"), full_page=False)
        print("page errors:", errors[:10])
        await browser.close()

        # verdict
        price_ok = rec_price.replace(" ", "").replace("₽", "").strip() == sku_price.replace(" ", "").replace("₽", "").strip()
        unit_ok = has_ozon_unit and (new_cols.get("unit") or "").replace(" ", "").replace("—", "") != ""
        rec_price_ok = has_rec_price and (new_cols.get("rec") or "").replace(" ", "").replace("—", "") != ""
        ok = (
            has_chart
            and sku_active
            and rows > 10
            and rows2 < rows
            and len(canvases) >= 5
            and cost_rows > 0
            and rec_rows > 0
            and pf.get("w", 0) > 0
            and idx.get("w", 0) > 0
            and wb.get("w", 0) > 0
            and err_vis in ("none", "", None)
            and price_ok
            and len(comp_seller) > 3
            and unit_ok
            and rec_price_ok
        )
        print("price_match", price_ok, "competitor_col_ok", len(comp_seller) > 3)
        print("ozon_unit_col_ok", unit_ok, "rec_price_col_ok", rec_price_ok)
        print("SMOKE_OK" if ok else "SMOKE_FAIL")


if __name__ == "__main__":
    asyncio.run(main())
