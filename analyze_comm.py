import json
prices = json.load(open(r"C:\Users\Alex\ozon_analytics\ozon_prices_full.json", encoding="utf-8"))
for p in prices[:8]:
    pr = p["price"]["price"]
    ac = p.get("acquiring")
    sp = p["commissions"].get("sales_percent_fbs")
    acq_pct = round(ac / pr * 100, 3) if pr and ac is not None else None
    print(
        f"offer={p['offer_id']} price={pr} old={p['price'].get('old_price')} "
        f"acquiring={ac} acq%={acq_pct} sales_pct={sp} "
        f"log_fbs={p['commissions'].get('fbs_direct_flow_trans_min_amount')}-"
        f"{p['commissions'].get('fbs_direct_flow_trans_max_amount')} vat={p['price'].get('vat')}"
    )

aps = []
for p in prices:
    pr = p["price"]["price"]
    ac = p.get("acquiring")
    if pr and ac is not None:
        aps.append(ac / pr * 100)
print("acquiring % min/avg/max", round(min(aps), 3), round(sum(aps) / len(aps), 3), round(max(aps), 3))

# commission by percent value: avg price
from collections import defaultdict

by = defaultdict(list)
for p in prices:
    by[p["commissions"].get("sales_percent_fbs")].append(p["price"]["price"])
for k, v in sorted(by.items(), key=lambda x: (x[0] is None, x[0])):
    print(f"sales_percent={k} n={len(v)} avg_price={round(sum(v)/len(v),1)}")
