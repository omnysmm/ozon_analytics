import json

for fname in ("sku_economics.json", "website_data.json"):
    d = json.load(open(fname, encoding="utf-8"))
    print("===", fname, type(d).__name__, len(d) if hasattr(d, "__len__") else "")
    rows = d
    if isinstance(d, dict):
        for k in ("skus", "items", "data", "sku"):
            if k in d:
                rows = d[k]
                print(" key", k, "len", len(rows))
                break
        else:
            print(" dict keys:", list(d.keys())[:20])
            rows = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        offer = r.get("offer_id") or r.get("offer") or r.get("sku") or ""
        if offer != "NK5415":
            continue
        keys = ["offer_id", "offer", "name", "price_ozon", "price", "current_price", "seller_price_api",
                "avg_sale_price", "current_avg_price", "competitor_price", "competitor_seller",
                "competitor_source", "ozon_final_price", "min_price", "qty", "revenue"]
        print({k: r.get(k) for k in keys if k in r})
        print(" all price-like:", {k: v for k, v in r.items() if "price" in k.lower() or "cost" in k.lower() or "цена" in k.lower()})
