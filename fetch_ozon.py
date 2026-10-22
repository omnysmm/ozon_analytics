#!/usr/bin/env python3
"""Fetch Ozon catalog + price/commission data (read-only)."""
import json
import time
import requests
from ozon_secrets import ozon_headers

H = ozon_headers()
BASE = "https://api-seller.ozon.ru"
OUT = r"C:\Users\Alex\ozon_analytics"


def fetch_all_products():
    items = []
    last_id = ""
    while True:
        body = {"filter": {"visibility": "ALL"}, "limit": 1000}
        if last_id:
            body["last_id"] = last_id
        r = requests.post(f"{BASE}/v3/product/list", headers=H, json=body, timeout=30)
        d = r.json()["result"]
        items.extend(d["items"])
        last_id = d.get("last_id", "")
        print(f"products {len(items)} / {d.get('total_items')}", flush=True)
        if not last_id or len(items) >= d.get("total_items", 0):
            break
    return items


def fetch_prices(ids):
    prices = []
    for i in range(0, len(ids), 1000):
        chunk = ids[i : i + 1000]
        r = requests.post(
            f"{BASE}/v5/product/info/prices",
            headers=H,
            json={"filter": {"product_id": chunk}, "limit": 1000},
            timeout=60,
        )
        data = r.json()
        items = data.get("items", [])
        prices.extend(items)
        print(f"prices {len(prices)}", flush=True)
        time.sleep(0.25)
    return prices


def fetch_info(ids):
    infos = []
    for i in range(0, len(ids), 1000):
        chunk = ids[i : i + 1000]
        r = requests.post(
            f"{BASE}/v3/product/info/list",
            headers=H,
            json={"product_id": chunk},
            timeout=60,
        )
        data = r.json()
        items = data.get("result", {}).get("items", [])
        infos.extend(items)
        print(f"infos {len(infos)}", flush=True)
        time.sleep(0.25)
    return infos


def probe_finance():
    """Probe finance/order endpoints and record what works."""
    from datetime import date, timedelta

    end = date.today()
    start = end - timedelta(days=35)
    from_s = f"{start}T00:00:00.000Z"
    to_s = f"{end}T23:59:59.000Z"
    endpoints = [
        ("/v1/finance/transaction-list", {"filter": {"date": {"from": from_s, "to": to_s}, "transaction_type": "all"}, "page": 1, "page_size": 5}),
        ("/v1/finance/cash-flow-statement", {"date": {"from": from_s, "to": to_s}}),
        ("/v3/posting/fbs/list", {"dir": "ASC", "filter": {"since": from_s, "to": to_s}, "limit": 5, "offset": 0, "with": {"analytics_data": True, "financial_data": True}}),
        ("/v3/posting/fbo/list", {"dir": "ASC", "filter": {"since": from_s, "to": to_s}, "limit": 5, "offset": 0, "with": {"financial_data": True}}),
        ("/v2/posting/fbs/act/create", {"date": {"from": from_s, "to": to_s}}),
        ("/v1/finance/act/create", {"date": {"from": from_s, "to": to_s}}),
        ("/v1/posting/fbs/list", {"dir": "ASC", "filter": {"since": from_s, "to": to_s}, "limit": 5, "offset": 0}),
        ("/v2/supplier/finance/realization", {"date": {"from": from_s, "to": to_s}}),
        ("/v1/supplier/finance/realization", {"date": {"from": from_s, "to": to_s}}),
    ]
    results = []
    for path, body in endpoints:
        try:
            r = requests.post(f"{BASE}{path}", headers=H, json=body, timeout=30)
            entry = {
                "path": path,
                "status": r.status_code,
                "body": r.text[:600],
            }
        except Exception as e:
            entry = {"path": path, "status": "ERR", "body": str(e)}
        results.append(entry)
        print(path, entry["status"], entry["body"][:200], flush=True)
    with open(f"{OUT}\\finance_probe.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    return results


def main():
    products = fetch_all_products()
    with open(f"{OUT}\\ozon_products_list.json", "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False)

    ids = [p["product_id"] for p in products]
    prices = fetch_prices(ids)
    with open(f"{OUT}\\ozon_prices_full.json", "w", encoding="utf-8") as f:
        json.dump(prices, f, ensure_ascii=False)

    infos = fetch_info(ids)
    with open(f"{OUT}\\ozon_product_info.json", "w", encoding="utf-8") as f:
        json.dump(infos, f, ensure_ascii=False)

    probe_finance()

    if prices:
        print("\n=== SAMPLE PRICE ===")
        print(json.dumps(prices[0], ensure_ascii=False, indent=2)[:3000])
    print("DONE")


if __name__ == "__main__":
    main()
