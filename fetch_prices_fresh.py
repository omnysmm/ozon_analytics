"""Fetch fresh price indexes only (read-only). items is top-level in /v5/product/info/prices."""
import json
import time
from pathlib import Path

import requests
import urllib3

urllib3.disable_warnings()
OUT = Path(r"C:\Users\Alex\ozon_analytics")
cfg = json.load(open(OUT / "ozon_config.json", encoding="utf-8"))
S = requests.Session()
S.verify = False
S.headers.update({
    "Content-Type": "application/json",
    "Client-Id": str(cfg["ozon_client_id"]),
    "Api-Key": cfg["ozon_api_key_extended"],
})
BASE = "https://api-seller.ozon.ru"


def post(path, body, retries=6):
    for i in range(retries):
        r = S.post(BASE + path, json=body, timeout=45)
        if r.status_code == 200:
            return r.json()
        if r.status_code == 429:
            time.sleep(2 + i * 2)
            continue
        print("ERR", r.status_code, r.text[:200])
        return None
    return None


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
    print("product ids", len(ids), flush=True)
    if not last_id or not items:
        break
    time.sleep(1.0)

time.sleep(1.5)
prices = []
for i in range(0, len(ids), 100):
    chunk = ids[i:i + 100]
    res = post("/v5/product/info/prices", {"filter": {"product_id": chunk}, "limit": 1000})
    if res:
        batch = res.get("result", {}).get("items") or res.get("items") or []
        prices.extend(batch)
        print("prices chunk", i, "got", len(batch), "total", len(prices), flush=True)
    time.sleep(1.5)

json.dump(prices, open(OUT / "price_indexes_fresh.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("saved", len(prices))
if prices:
    print(json.dumps(prices[0], ensure_ascii=False)[:800])
