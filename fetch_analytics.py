"""Fetch Ozon analytics (sku + day) with rate-limit handling."""
import requests
import json
import time
from datetime import date, timedelta
from ozon_secrets import ozon_headers

H = ozon_headers()
BASE = "https://api-seller.ozon.ru"
OUT = r"C:\Users\Alex\ozon_analytics"

end = date.today()
start = end - timedelta(days=45)


def fetch_analytics(dimension, metrics, limit=500, label=""):
    offset = 0
    all_rows = []
    while True:
        body = {
            "date_from": str(start),
            "date_to": str(end),
            "metrics": metrics,
            "dimension": dimension,
            "limit": limit,
            "offset": offset,
        }
        for attempt in range(6):
            r = requests.post(f"{BASE}/v1/analytics/data", headers=H, json=body, timeout=30)
            if r.status_code == 200:
                break
            if r.status_code == 429:
                wait = 1.5 * (attempt + 1)
                print(f"  rate-limit {label}, wait {wait}s", flush=True)
                time.sleep(wait)
                continue
            print(f"  ERR {label} {r.status_code} {r.text[:200]}", flush=True)
            return all_rows
        data = r.json().get("result", {})
        rows = data.get("data", [])
        all_rows.extend(rows)
        print(f"{label} offset={offset} got={len(rows)} total={len(all_rows)}", flush=True)
        if len(rows) < limit:
            break
        offset += limit
        time.sleep(1.2)
    return all_rows


if __name__ == "__main__":
    # 1) by day
    days = fetch_analytics(
        ["day"],
        ["revenue", "ordered_units", "returns", "cancellations", "session_view"],
        limit=100,
        label="days",
    )
    with open(f"{OUT}\\analytics_days.json", "w", encoding="utf-8") as f:
        json.dump(days, f, ensure_ascii=False, indent=1)

    time.sleep(2)

    # 2) by sku
    skus = fetch_analytics(
        ["sku"],
        ["revenue", "ordered_units", "returns", "cancellations", "session_view"],
        limit=1000,
        label="skus",
    )
    with open(f"{OUT}\\analytics_skus.json", "w", encoding="utf-8") as f:
        json.dump(skus, f, ensure_ascii=False, indent=1)

    time.sleep(2)

    # 3) by brand / category if available
    for dim in (["brand"], ["category"]):
        try:
            rows = fetch_analytics(dim, ["revenue", "ordered_units"], limit=100, label=str(dim))
            with open(f"{OUT}\\analytics_{dim[0]}.json", "w", encoding="utf-8") as f:
                json.dump(rows, f, ensure_ascii=False, indent=1)
            time.sleep(1.5)
        except Exception as e:
            print(dim, e)

    print("DONE")
    print("days sample", days[:3] if days else None)
    print("skus sample", skus[:3] if skus else None)
