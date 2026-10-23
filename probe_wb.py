"""Probe WB statistics/supplier APIs (read-only) and report what works."""
import json
from datetime import date, timedelta
from pathlib import Path
import requests

from ozon_secrets import wb_headers

OUT = Path(r"C:\Users\Alex\ozon_analytics")
H = wb_headers()
end = date.today()
start = end - timedelta(days=45)
rr = f"{start}T00:00:00.000000000"

PROBES = [
    ("statistics-api", "GET", "https://statistics-api.wildberries.ru/api/v1/supplier/sales", {"dateFrom": rr}),
    ("statistics-api", "GET", "https://statistics-api.wildberries.ru/api/v1/supplier/stocks", {"dateFrom": rr}),
    ("statistics-api", "GET", "https://statistics-api.wildberries.ru/api/v1/supplier/incomes", {"dateFrom": rr}),
    ("statistics-api", "GET", "https://statistics-api.wildberries.ru/api/v1/supplier/orders", {"dateFrom": rr}),
    ("statistics-api", "GET", "https://statistics-api.wildberries.ru/api/v1/supplier/reportDetailByPeriod", {"dateFrom": str(start), "dateTo": str(end), "rrdId": "0"}),
    ("prices-api", "GET", "https://suppliers-api.wildberries.ru/public/api/v1/info", None),
    ("content-api", "GET", "https://content-api.wildberries.ru/content/v2/get/cards/list", None),
    ("seller-api", "GET", "https://statistics-api.wildberries.ru/api/v1/supplier/reportDetailByPeriod", {"dateFrom": str(start), "dateTo": str(end)}),
]

results = {}
for name, method, url, params in PROBES:
    key = url.split("/")[-1] + ("?detail" if "reportDetail" in url else "")
    try:
        if method == "GET":
            r = requests.get(url, headers=H, params=params, timeout=60)
        else:
            r = requests.post(url, headers=H, json=params or {}, timeout=60)
        raw = r.text
        item = {"status": r.status_code, "len": len(raw), "url": url, "params": params}
        if r.status_code == 200:
            try:
                data = r.json()
                if isinstance(data, list):
                    item["count"] = len(data)
                    item["sample_keys"] = list(data[0].keys())[:25] if data else []
                    item["sample0"] = data[0] if data else None
                elif isinstance(data, dict):
                    item["keys"] = list(data.keys())[:30]
                    for k in ("data", "cards", "value", "errors"):
                        if k in data and isinstance(data[k], list):
                            item[f"{k}_count"] = len(data[k])
                            if data[k] and isinstance(data[k][0], dict):
                                item[f"{k}_keys"] = list(data[k][0].keys())[:25]
                                item[f"{k}_0"] = data[k][0]
            except Exception as e:
                item["parse_err"] = str(e)
                item["head"] = raw[:300]
        else:
            item["body"] = raw[:400]
    except Exception as e:
        item = {"error": str(e), "url": url}
    results[key] = item
    print("=", key, item.get("status"), item.get("count") or item.get("len") or item.get("error"),
          "keys", item.get("sample_keys") or item.get("keys") or "")

json.dump(results, open(OUT / "wb_probe.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
print("wrote wb_probe.json")
