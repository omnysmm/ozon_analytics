"""Headed Edge / dedicated-profile Chrome for Ozon seller names."""
import json
import re
import traceback
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(r"C:\Users\Alex\ozon_analytics")
PIDS = {"NK5415": 255832676, "NK54125": 306414751, "I-D-P": 1424446737}
PATS = [
    r'"sellerName"\s*:\s*"([^"]{2,80})"',
    r'"brandName"\s*:\s*"([^"]{2,80})"',
    r'"seller_name"\s*:\s*"([^"]{2,80})"',
]


def sellers_from(text):
    out = []
    for p in PATS:
        out.extend(re.findall(p, text))
    return list(dict.fromkeys(out))[:15]


def run(channel, user_data_dir=None, headless=False):
    print(f"\n=== channel={channel} headless={headless} profile={user_data_dir} ===")
    results = {}
    with sync_playwright() as p:
        kw = {
            "headless": headless,
            "args": ["--disable-blink-features=AutomationControlled", "--no-first-run", "--no-default-browser-check"],
        }
        if channel:
            kw["channel"] = channel
        if user_data_dir:
            kw["user_data_dir"] = str(user_data_dir)
        try:
            if user_data_dir:
                context = p.chromium.launch_persistent_context(str(user_data_dir), **{k: v for k, v in kw.items() if k != "user_data_dir"})
                page = context.new_page()
                browser = None
            else:
                browser = p.chromium.launch(**kw)
                context = browser.new_context(
                    locale="ru-RU",
                    timezone_id="Europe/Moscow",
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
                )
                page = context.new_page()
        except Exception as e:
            print("LAUNCH FAIL", e)
            return {"launch_error": str(e)}

        try:
            page.goto("https://www.ozon.ru/", wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(6000)
            print("home", page.title(), "html", len(page.content()), "url", page.url)
            for offer, pid in PIDS.items():
                url = f"https://www.ozon.ru/product/{pid}/"
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=60000)
                    page.wait_for_timeout(7000)
                    html = page.content()
                    sl = sellers_from(html)
                    # also look for visible seller text
                    try:
                        vis = page.evaluate("""() => {
                          const t = document.body.innerText || '';
                          const m = t.match(/Продавец[:\\s]+([^\\n]{2,60})/i);
                          return m ? m[1].trim() : null;
                        }""")
                    except Exception:
                        vis = None
                    results[offer] = {"status": 200, "len": len(html), "title": page.title(), "url": page.url, "sellers": sl, "visible_seller": vis}
                    print(offer, "len", len(html), "sellers", sl[:5], "vis", vis)
                    if offer == "NK5415":
                        page.screenshot(path=str(OUT / "ozon_seller_sample.png"))
                except Exception as e:
                    results[offer] = {"error": str(e)}
                    print("ERR", offer, e)
        except Exception as e:
            print("NAV FAIL", e)
            traceback.print_exc()
            results["_nav"] = {"error": str(e)}
        finally:
            try:
                if user_data_dir:
                    context.close()
                else:
                    context.close()
                    browser.close()
            except Exception:
                pass
    return results


def main():
    all_res = {}
    # 1) Edge headed, dedicated profile
    prof = OUT / ".edge_profile"
    prof.mkdir(exist_ok=True)
    all_res["edge_headed"] = run("msedge", user_data_dir=prof, headless=False)
    # 2) Chromium headed, dedicated profile
    prof2 = OUT / ".chr_profile"
    prof2.mkdir(exist_ok=True)
    all_res["chr_headed"] = run(None, user_data_dir=prof2, headless=False)
    json.dump(all_res, open(OUT / "competitors_sellers3.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\nwrote competitors_sellers3.json")
    for k, v in all_res.items():
        if isinstance(v, dict) and v.get("NK5415", {}).get("sellers"):
            print("SUCCESS path", k, v["NK5415"]["sellers"][:5])


if __name__ == "__main__":
    main()
