"""Open Google Sheet in real Chrome profile and export values (read-only)."""
import asyncio
import json
import sys

from playwright.async_api import async_playwright

SHEET_URL = "https://docs.google.com/spreadsheets/d/1dk_S--7vyExaBSn5MY9KLiI8HIAA6Ypo/edit?gid=1988518778#gid=1988518778"
EXPORT_CSV = "https://docs.google.com/spreadsheets/d/1dk_S--7vyExaBSn5MY9KLiI8HIAA6Ypo/export?format=csv&gid=1988518778"
EXPORT_XLSX = "https://docs.google.com/spreadsheets/d/1dk_S--7vyExaBSn5MY9KLiI8HIAA6Ypo/export?format=xlsx"
USER_DATA = r"C:\Users\Alex\AppData\Local\Google\Chrome\User Data"
OUT = r"C:\Users\Alex\ozon_analytics"


async def main():
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            USER_DATA,
            channel="chrome",
            headless=True,
            viewport={"width": 1400, "height": 900},
            args=["--profile-directory=Default"],
        )
        page = context.pages[0] if context.pages else await context.new_page()

        # try CSV export first
        resp = await page.goto(EXPORT_CSV, wait_until="domcontentloaded", timeout=60000)
        print("csv status", resp.status if resp else None)
        body = await page.content()
        print("csv body len", len(body))
        print(body[:500])

        # save whatever we got
        try:
            text = await page.evaluate("document.body.innerText")
        except Exception:
            text = body
        open(f"{OUT}\\gsheet_csv_dump.txt", "w", encoding="utf-8").write(text[:200000])

        # also try the edit page to see if we are logged in
        resp2 = await page.goto(SHEET_URL, wait_until="domcontentloaded", timeout=60000)
        print("edit status", resp2.status if resp2 else None)
        title = await page.title()
        print("title", title)
        await page.screenshot(path=f"{OUT}\\gsheet.png", full_page=False)

        # try xlsx export
        resp3 = await page.goto(EXPORT_XLSX, wait_until="domcontentloaded", timeout=60000)
        print("xlsx status", resp3.status if resp3 else None)

        await context.close()


if __name__ == "__main__":
    asyncio.run(main())
