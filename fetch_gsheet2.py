"""Try Edge profile + cookie-based Google Sheets export (read-only)."""
import asyncio
import json
import os
import shutil
import sqlite3
import tempfile
from pathlib import Path

from playwright.async_api import async_playwright

SHEET_ID = "1dk_S--7vyExaBSn5MY9KLiI8HIAA6Ypo"
GID = "1988518778"
OUT = Path(r"C:\Users\Alex\ozon_analytics")

EXPORTS = [
    f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}",
    f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=xlsx",
    f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&gid={GID}",
    f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit?gid={GID}",
]


async def try_persistent(channel, user_data, profile_dir, label):
    print(f"\n=== TRY {label} ===")
    async with async_playwright() as p:
        kw = dict(
            headless=True,
            viewport={"width": 1400, "height": 900},
            args=[f"--profile-directory={profile_dir}"],
        )
        if channel:
            kw["channel"] = channel
        try:
            context = await p.chromium.launch_persistent_context(str(user_data), **kw)
        except Exception as e:
            print("launch fail", e)
            return False
        page = context.pages[0] if context.pages else await context.new_page()
        ok = False
        for url in EXPORTS:
            try:
                resp = await page.goto(url, wait_until="domcontentloaded", timeout=45000)
                status = resp.status if resp else None
                text = ""
                try:
                    text = await page.evaluate("document.body ? document.body.innerText : ''")
                except Exception:
                    pass
                ct = ""
                try:
                    ct = (resp.headers or {}).get("content-type", "") if resp else ""
                except Exception:
                    pass
                print(f"  {status} {ct} len={len(text)} {url[:80]}")
                if status == 200 and text and "Sign in" not in text[:200] and "Войдите" not in text[:200]:
                    fn = OUT / f"gsheet_{label}_{url[-20:].replace('/','_').replace('?','_')}.txt"
                    fn.write_text(text[:300000], encoding="utf-8")
                    print("  SAVED", fn)
                    ok = True
                if "export?format=xlsx" in url and status == 200:
                    # download via page response
                    pass
            except Exception as e:
                print("  nav err", e)
        await page.goto(f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit?gid={GID}", wait_until="domcontentloaded", timeout=45000)
        await page.screenshot(path=str(OUT / f"gsheet_{label}.png"))
        title = await page.title()
        print("  title:", title)
        await context.close()
        return ok


async def main():
    # 1) Edge
    edge_ud = r"C:\Users\Alex\AppData\Local\Microsoft\Edge\User Data"
    if os.path.isdir(edge_ud):
        await try_persistent("msedge", edge_ud, "Default", "edge")

    # 2) Chrome temp copy (avoid lock)
    chrome_ud = r"C:\Users\Alex\AppData\Local\Google\Chrome\User Data"
    tmp = Path(tempfile.gettempdir()) / "chrome_ozon_profile"
    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True, exist_ok=True)
    # copy only cookie + login data
    for name in ("Default/Cookies", "Default/Login Data", "Local State", "Default/Network/Cookies"):
        src = Path(chrome_ud) / name
        if src.exists():
            dst = tmp / name
            dst.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.copy2(src, dst)
                print("copied", name)
            except Exception as e:
                print("copy fail", name, e)
    await try_persistent(None, tmp, "Default", "chrome_copy")


if __name__ == "__main__":
    asyncio.run(main())
