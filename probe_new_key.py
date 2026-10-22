"""Probe new Ozon key for analytics + finance; save whatever is available."""
import requests
import json
import time
from datetime import date, timedelta
from ozon_secrets import ozon_headers

H = ozon_headers()
BASE = "https://api-seller.ozon.ru"
OUT = r"C:\Users\Alex\ozon_analytics"

end = date.today()
start = end - timedelta(days=40)
from_s = f"{start}T00:00:00.000Z"
to_s = f"{end}T23:59:59.000Z"

results = []


def probe(path, body, note=""):
    try:
        r = requests.post(f"{BASE}{path}", headers=H, json=body, timeout=30)
        entry = {"path": path, "note": note, "status": r.status_code, "body": r.text[:2000]}
    except Exception as e:
        entry = {"path": path, "note": note, "status": "ERR", "body": str(e)}
    results.append(entry)
    print(f"{path:50s} {entry['status']} {entry['body'][:180].replace(chr(10),' ')}", flush=True)
    return entry


# analytics (rate-limited earlier) — retry with sleep
print("=== ANALYTICS ===")
time.sleep(2)
probe(
    "/v1/analytics/data",
    {
        "date_from": f"{start}",
        "date_to": f"{end}",
        "metrics": ["revenue", "ordered_units", "returns", "cancellations"],
        "dimension": ["sku"],
        "limit": 100,
        "offset": 0,
    },
    "analytics sku metrics",
)

time.sleep(2)
probe(
    "/v1/analytics/data",
    {
        "date_from": f"{start}",
        "date_to": f"{end}",
        "metrics": ["revenue", "ordered_units"],
        "dimension": ["day"],
        "limit": 100,
        "offset": 0,
    },
    "analytics day",
)

# finance path variants
print("=== FINANCE PATHS ===")
fin_paths = [
    "/v1/finance/transaction-list",
    "/v1/finance/transaction-list/list",
    "/v1/finance/transaction/list",
    "/v3/finance/transaction-list",
    "/api/finance/transaction-list",
    "/v1/finance/cash-flow-statement",
    "/v1/finance/cash-flow",
    "/v1/supplier/finance/realization",
    "/v1/finance/realization",
    "/v2/finance/transaction-list",
    "/v1/finance/transactions",
]
body_fin = {
    "filter": {"date": {"from": from_s, "to": to_s}, "transaction_type": "all"},
    "page": 1,
    "page_size": 3,
}
for p in fin_paths:
    time.sleep(0.4)
    probe(p, body_fin, "finance variant")

# postings
print("=== POSTINGS ===")
time.sleep(1)
probe(
    "/v3/posting/fbs/list",
    {
        "dir": "ASC",
        "filter": {"since": from_s, "to": to_s},
        "limit": 3,
        "offset": 0,
        "with": {"analytics_data": True, "financial_data": True},
    },
    "fbs list",
)

# act reports
probe("/v2/posting/fbs/act/create", {"date": {"from": from_s, "to": to_s}}, "act create")
probe("/v1/posting/fbs/act/get-pdf", {"id": 1}, "act pdf")

# product attributes / stocks read
print("=== PRODUCT EXTRAS ===")
probe("/v2/product/info/prices", {"filter": {"offer_id": ["NK5415"]}, "limit": 1}, "prices v2")
probe(
    "/v2/products/stocks",
    {"stocks": [{"offer_id": "NK5415", "stock": 1, "warehouse_id": 1}]},
    "stocks validate",
)

# warehouse list (read)
probe("/v1/warehouse/list", {}, "warehouses")

with open(f"{OUT}\\finance_probe_v2.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print("\nDONE saved", len(results))
