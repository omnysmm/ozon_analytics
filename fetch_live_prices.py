"""Fetch live Ozon prices from /v3/product/info/list for all SKUs (read-only)."""
import json
import time
import requests
from pathlib import Path
from ozon_secrets import ozon_headers

OUT = Path(r"C:\Users\Alex\ozon_analytics")
H = ozon_headers()
BASE = "https://api-seller.ozon.ru"

products = json.load(open(OUT / "ozon_products_list.json", encoding="utf-8"))
ids = [p["product_id"] for p in products]
print("products", len(ids))

infos = []
for i in range(0, len(ids), 500):
    chunk = ids[i : i + 500]
    r = requests.post(f"{BASE}/v3/product/info/list", headers=H, json={"product_id": chunk}, timeout=60)
    data = r.json()
    items = data.get("result", {}).get("items", []) or data.get("items", [])
    infos.extend(items)
    print("infos", len(infos), "status", r.status_code)
    time.sleep(0.4)

# index by offer_id
by_offer = {}
for it in infos:
    offer = it.get("offer_id")
    if not offer:
        continue
    try:
        price = float(it.get("price") or 0)
    except Exception:
        price = 0
    try:
        min_price = float(it.get("min_price") or 0)
    except Exception:
        min_price = 0
    try:
        old_price = float(it.get("old_price") or 0)
    except Exception:
        old_price = 0
    by_offer[offer] = {
        "product_id": it.get("id"),
        "offer_id": offer,
        "name": it.get("name") or "",
        "price_ozon": price,          # CURRENT price on Ozon (live)
        "min_price_ozon": min_price,
        "old_price_ozon": old_price,
        "barcodes": it.get("barcodes") or [],
        "images": (it.get("images") or [])[:3],
    }

print("offers", len(by_offer))
# sample
for o in ["NK5415", "NK54125", "PSGRAY", "I-D-P"]:
    print(o, by_offer.get(o))

json.dump(by_offer, open(OUT / "ozon_live_prices.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("saved ozon_live_prices")
