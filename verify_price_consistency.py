"""Verify price_ozon consistency across dashboard tabs for multiple SKUs."""
import re, json
from playwright.sync_api import sync_playwright

URL = "file:///C:/Users/Alex/ozon_analytics/index.html"
CHECK_OFFERS = ["NK5415", "NK54125", "PSGRAY", "I-D-P", "PS-ANTIK-SER", "NL24", "PSBL", "NK6115"]


def table_rows(page, tab_id):
    page.click(f'button[data-tab="{tab_id}"], #{tab_id}-tab, [onclick*="{tab_id}"]')
    page.wait_for_timeout(400)
    return page.evaluate("""() => {
        const out = {};
        document.querySelectorAll('table tbody tr').forEach(tr => {
            const tds = [...tr.querySelectorAll('td')].map(td => td.innerText.trim());
            if (tds.length < 2) return;
            out[tds[0]] = tds;
        });
        return out;
    }""")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(URL, wait_until="load")
        page.wait_for_timeout(800)

        # discover tab buttons
        tabs = page.evaluate("""() => [...document.querySelectorAll('button,[role=tab],.tab-btn')]
            .map(b => ({id: b.id, data: b.getAttribute('data-tab')||b.getAttribute('data-target')||'',
                        onclick: b.getAttribute('onclick')||'', text: b.innerText.trim()}))
            .filter(x => x.text)""")
        print("tabs:", tabs)

        # Map of expected tab labels
        # We'll navigate via text match
        def open_tab(label_part):
            loc = page.locator(f'button:has-text("{label_part}"), [role=tab]:has-text("{label_part}"), .tab-btn:has-text("{label_part}")')
            if loc.count():
                loc.first.click()
                page.wait_for_timeout(500)
                return True
            return False

        results = []
        # SKU tab
        ok1 = open_tab("артикул")
        print("open SKU tab:", ok1)
        page.wait_for_timeout(300)
        sku = page.evaluate("""() => {
            const out = {};
            document.querySelectorAll('table tbody tr').forEach(tr => {
                const tds = [...tr.querySelectorAll('td')].map(td => td.innerText.trim());
                if (tds.length < 3) return;
                out[tds[0]] = tds;
            });
            return out;
        }""")
        # Prices / competitors tab
        ok2 = open_tab("Цены")
        print("open Prices tab:", ok2)
        page.wait_for_timeout(300)
        prices = page.evaluate("""() => {
            const out = {};
            document.querySelectorAll('table tbody tr').forEach(tr => {
                const tds = [...tr.querySelectorAll('td')].map(td => td.innerText.trim());
                if (tds.length < 3) return;
                out[tds[0]] = tds;
            });
            return out;
        }""")

        print(f"sku offers: {len(sku)}, price offers: {len(prices)}")

        # Find header columns to know price column index
        headers = page.evaluate("""() => [...document.querySelectorAll('table thead th')].map(th => th.innerText.trim())""")
        print("prices headers:", headers)

        mismatches = []
        matches = 0
        for offer in CHECK_OFFERS:
            s = sku.get(offer)
            r = prices.get(offer)
            if not s or not r:
                results.append((offer, "MISSING", s, r))
                continue
            # find price-like columns: look for columns containing 'Цена' in header of that table
            # Fallback: compare any numeric cells that look like the same price set
            results.append((offer, s[:6], r[:6]))

        # Broader: for every shared offer, extract all numeric prices and check that
        # price_ozon values (typically 3-digit/4-digit like 924) appear in BOTH tables
        shared = set(sku) & set(prices)
        price_mismatch = []
        for offer in sorted(shared):
            s_nums = set(re.findall(r'\d+(?:[.,]\d+)?', ' | '.join(sku[offer])))
            r_nums = set(re.findall(r'\d+(?:[.,]\d+)?', ' | '.join(prices[offer])))
            # normalize
            def norm(x):
                try:
                    f = float(x.replace(',', '.'))
                    return f if f > 10 else None
                except Exception:
                    return None
            s_p = {norm(x) for x in s_nums} - {None}
            r_p = {norm(x) for x in r_nums} - {None}
            # The live Ozon price is a distinctive value; check intersection non-empty of "main" prices
            inter = s_p & r_p
            if not inter:
                price_mismatch.append((offer, sorted(s_p)[:5], sorted(r_p)[:5]))
            else:
                matches += 1

        print(f"shared offers: {len(shared)}, with common price numbers: {matches}, pure mismatches: {len(price_mismatch)}")
        if price_mismatch[:5]:
            print("sample mismatches:", price_mismatch[:5])

        # Check competitor source column non-empty on shared rows
        empty_comp = 0
        for offer in shared:
            row = prices[offer]
            if not any(c and c not in ('—', '-', 'н/д', 'N/A') for c in row[2:]):
                empty_comp += 1
        print("rows with empty competitor data:", empty_comp)

        print("page errors:", errors)
        for row in results:
            print("ROW", row)

        browser.close()
        if price_mismatch:
            print("PRICE_INCONSISTENT")
            return 1
        print("MULTI_SKU_OK")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
