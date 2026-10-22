"""Check column borders visible + text reveals after widening."""
from pathlib import Path
from playwright.sync_api import sync_playwright

URL = Path(r"C:\Users\Alex\ozon_analytics\index.html").resolve().as_uri()

with sync_playwright() as p:
    b = p.chromium.launch()
    page = b.new_page(viewport={"width": 1500, "height": 950})
    page.goto(URL, wait_until="load")
    page.wait_for_timeout(600)
    page.click('button[data-tab="sku"]')
    page.wait_for_timeout(300)

    # borders present
    borders = page.evaluate("""() => {
      const td = document.querySelector('#skuTable tbody tr td');
      const th = document.querySelector('#skuTable thead th');
      const csTd = getComputedStyle(td), csTh = getComputedStyle(th);
      return {
        tdRight: csTd.borderRightWidth + ' ' + csTd.borderRightColor,
        thRight: csTh.borderRightWidth + ' ' + csTh.borderRightColor,
        menuLabelAlign: getComputedStyle(document.querySelector('#colMenuSku label') || document.body).justifyContent
      };
    }""")
    print("borders", borders)

    # name cell clipping before/after
    # find NK5415 row name cell (index 1)
    page.fill("#fSearch", "NK5415")
    page.wait_for_timeout(300)
    before = page.evaluate("""() => {
      const tr = document.querySelector('#skuTable tbody tr');
      const td = tr.children[1];
      return {
        text: td.innerText.trim(),
        cw: td.clientWidth,
        sw: td.scrollWidth,
        clipped: td.scrollWidth > td.clientWidth + 2
      };
    }""")
    print("name before", before)

    # widen name column via resizer on th[1]
    box = page.evaluate("""() => {
      const th = document.querySelectorAll('#skuTable thead th')[1];
      const g = th.querySelector('.resizer').getBoundingClientRect();
      return {gx: g.x + g.width/2, gy: g.y + g.height/2, w: th.getBoundingClientRect().width};
    }""")
    page.mouse.move(box["gx"], box["gy"])
    page.mouse.down()
    page.mouse.move(box["gx"] + 160, box["gy"], steps=10)
    page.mouse.up()
    page.wait_for_timeout(200)
    after = page.evaluate("""() => {
      const tr = document.querySelector('#skuTable tbody tr');
      const td = tr.children[1];
      const th = document.querySelectorAll('#skuTable thead th')[1];
      return {
        text: td.innerText.trim(),
        cw: td.clientWidth,
        sw: td.scrollWidth,
        clipped: td.scrollWidth > td.clientWidth + 2,
        thW: th.getBoundingClientRect().width,
        maxW: getComputedStyle(td).maxWidth
      };
    }""")
    print("name after", after)

    # open col menu and check alignment
    page.click('[data-toggle="colMenuSku"]')
    page.wait_for_timeout(150)
    menu = page.evaluate("""() => {
      const menu = document.getElementById('colMenuSku');
      const lab = menu.querySelector('label');
      const cb = lab.querySelector('input');
      const lr = lab.getBoundingClientRect();
      const br = cb.getBoundingClientRect();
      return {
        menuLeft: menu.getBoundingClientRect().left,
        btnLeft: document.querySelector('[data-toggle=colMenuSku]').getBoundingClientRect().left,
        labelJustify: getComputedStyle(lab).justifyContent,
        cbOffsetFromLabelLeft: Math.round(br.left - lr.left)
      };
    }""")
    print("menu", menu)

    ok = (
        borders["tdRight"].startswith("1px")
        and after["cw"] > before["cw"] + 40
        and not after["clipped"]
        and after["maxW"] != "220px"
        and menu["cbOffsetFromLabelLeft"] <= 12
    )
    print("VISUAL_OK" if ok else "VISUAL_FAIL")
    b.close()
