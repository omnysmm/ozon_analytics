"""Fetch October 2026 sales per SKU + fresh competitor price indexes (read-only, retry on 429)."""
import json
import time
from pathlib import Path

import requests
import urllib3

urllib3.disable_warnings()
OUT = Path(r"C:\Users\Alex\ozon_analytics")
cfg = json.load(open(OUT / "ozon_config.json", encoding="utf-8"))
KEY = cfg["ozon_api_key_extended"]
CLIENT_ID = cfg["ozon_client_id"]

S = requests.Session()
S.verify = False
S.headers.update({"Content-Type": "application/json", "Client-Id": str(CLIENT_ID), "Api-Key": KEY})
BASE = "https://api-seller.ozon.ru"


def post(path, body, retries=6):
    for i in range(retries):
        r = S.post(BASE + path, json=body, timeout=45)
        if r.status_code == 200:
            return r.json()
        if r.status_code == 429:
            wait = 2 + i * 2
            print(f"  429 on {path}, sleep {wait}s", flush=True)
            time.sleep(wait)
            continue
        print(f"  ERR {r.status_code} {path}: {r.text[:200]}")
        return None
    return None


# ---------- 1) October sales by SKU ----------
rows = []
offset = 0
while True:
    body = {
        "date_from": "2026-10-01T00:00:00.000Z",
        "date_to": "2026-11-01T00:00:00.000Z",
        "metrics": ["revenue", "ordered_units", "returns", "session_view"],
        "dimension": ["sku"],
        "filters": [],
        "sort": [{"key": "revenue", "order": "DESC"}],
        "limit": 1000,
        "offset": offset,
    }
    res = post("/v1/analytics/data", body)
    if not res:
        break
    data = res.get("result", {}).get("data", [])
    for d in data:
        dims = d.get("dimensions", [])
        m = d.get("metrics", [])
        rows.append({
            "sku": dims[0]["id"] if dims else None,
            "name": dims[0].get("name") if dims else None,
            "revenue": m[0] if len(m) > 0 else 0,
            "ordered_units": m[1] if len(m) > 1 else 0,
            "returns": m[2] if len(m) > 2 else 0,
            "session_view": m[3] if len(m) > 3 else 0,
        })
    print("analytics got", len(data), "total", len(rows), flush=True)
    if len(data) < 1000:
        break
    offset += 1000
    time.sleep(1.5)

json.dump(rows, open(OUT / "oct_sales_by_sku.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("saved oct_sales_by_sku.json:", len(rows))

# ---------- 2) product ids ----------
time.sleep(1.5)
ids = []
last_id = ""
while True:
    body = {"filter": {"visibility": "ALL"}, "limit": 1000}
    if last_id:
        body["last_id"] = last_id
    res = post("/v3/product/list", body)
    if not res:
        break
    r = res.get("result", {})
    items = r.get("items", [])
    ids.extend(it["product_id"] for it in items)
    last_id = r.get("last_id", "") or ""
    print("product/list got", len(items), "total", len(ids), flush=True)
    if not last_id or not items:
        break
    time.sleep(1.0)

# ---------- 3) price indexes by product_id chunks ----------
time.sleep(1.5)
prices = []
for i in range(0, len(ids), 200):
    chunk = ids[i:i + 200]
    res = post("/v5/product/info/prices", {"filter": {"product_id": chunk}, "limit": 1000})
    if res:
        batch = res.get("result", {}).get("items", [])
        prices.extend(batch)
        print("prices chunk", i, "got", len(batch), "total", len(prices), flush=True)
    time.sleep(1.5)

json.dump(prices, open(OUT / "price_indexes_fresh.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("saved price_indexes_fresh.json:", len(prices))
