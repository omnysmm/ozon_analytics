"""Verify column resize grips + visibility picker on dashboard."""
from pathlib import Path
from playwright.sync_api import sync_playwright

URL = Path(r"C:\Users\Alex\ozon_analytics\index.html").resolve().as_uri()

with sync_playwright() as p:
    b = p.chromium.launch()
    page = b.new_page(viewport={"width": 1500, "height": 950})
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.goto(URL, wait_until="load")
    page.wait_for_timeout(800)
    page.click('button[data-tab="sku"]')
    page.wait_for_timeout(300)

    grips = page.evaluate("document.querySelectorAll('#skuTable th .resizer').length")
    headers = page.evaluate("document.querySelectorAll('#skuTable thead th').length")
    print("headers", headers, "resizers", grips)

    # open column menu
    page.click('[data-toggle="colMenuSku"]')
    page.wait_for_timeout(200)
    menu_open = page.evaluate("document.getElementById('colMenuSku').classList.contains('open')")
    checks = page.evaluate("document.querySelectorAll('#colMenuSku input[type=checkbox]').length")
    print("menu_open", menu_open, "checkboxes", checks)

    # uncheck 4th visible col (index 3 = price) — find by label
    page.evaluate("""() => {
      const labels = [...document.querySelectorAll('#colMenuSku label')];
      const cb = labels[3].querySelector('input');
      cb.click();
    }""")
    page.wait_for_timeout(200)
    hidden = page.evaluate("""() => {
      const th = document.querySelectorAll('#skuTable thead th')[3];
      const tr = document.querySelector('#skuTable tbody tr');
      return {
        thHidden: th.classList.contains('col-hidden'),
        tdHidden: tr && tr.children[3] && tr.children[3].classList.contains('col-hidden')
      };
    }""")
    print("after hide col3", hidden)

    # resize first column
    box = page.evaluate("""() => {
      const th = document.querySelectorAll('#skuTable thead th')[0];
      const r = th.getBoundingClientRect();
      const grip = th.querySelector('.resizer');
      const g = grip.getBoundingClientRect();
      return {thW: r.width, gx: g.x + g.width/2, gy: g.y + g.height/2};
    }""")
    page.mouse.move(box["gx"], box["gy"])
    page.mouse.down()
    page.mouse.move(box["gx"] + 80, box["gy"], steps=8)
    page.mouse.up()
    page.wait_for_timeout(150)
    new_w = page.evaluate("document.querySelectorAll('#skuTable thead th')[0].getBoundingClientRect().width")
    print("col0 width before", round(box["thW"], 1), "after", round(new_w, 1))

    # restore via menu "Сброс"
    page.click('[data-toggle="colMenuSku"]')
    page.wait_for_timeout(100)
    page.click('#colMenuSku .col-actions button:nth-child(2)')
    page.wait_for_timeout(200)
    restored = page.evaluate("""() => {
      const th = document.querySelectorAll('#skuTable thead th')[3];
      return !th.classList.contains('col-hidden');
    }""")
    print("restored col3 visible", restored)
    print("page errors", errs)
    ok = grips == headers and menu_open and checks == headers and hidden["thHidden"] and hidden["tdHidden"] and new_w > box["thW"] + 40 and restored and not errs
    print("COL_TOOLS_OK" if ok else "COL_TOOLS_FAIL")
    b.close()
