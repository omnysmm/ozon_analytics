"""Reverse-engineer per-transaction Ozon economics from charges report."""
import json
from collections import defaultdict

charges = json.load(open(r"C:\Users\Alex\ozon_analytics\charges_raw.json", encoding="utf-8"))

# group by id (transaction)
by_id = defaultdict(list)
for c in charges:
    by_id[c["id"]].append(c)

print("unique charge ids", len(by_id))

# find ids that have both revenue and commission
samples = []
for cid, items in by_id.items():
    types = {i["type"] for i in items}
    if "Выручка" in types and "Вознаграждение за продажу" in types:
        samples.append((cid, items))

print("ids with both revenue+commission", len(samples))

# show 8 sample transactions with all their lines
for cid, items in samples[:8]:
    print("\n" + "=" * 70)
    print("ID", cid)
    for i in sorted(items, key=lambda x: x["type"]):
        print(
            f"  {i['type'][:45]:45s} qty={i['qty']} price={i['price']} "
            f"amount={i['amount']:10.2f} reward%={i['reward_pct']} scheme={i['scheme']}"
        )

# aggregate per offer_id
agg = defaultdict(lambda: {
    "name": "",
    "qty_sold": 0,
    "revenue": 0.0,
    "commission": 0.0,
    "logistics": 0.0,
    "last_mile": 0.0,
    "acquiring": 0.0,
    "reverse_logistics": 0.0,
    "returns_fee": 0.0,
    "loyalty_points": 0.0,
    "partner_programs": 0.0,
    "premium": 0.0,
    "stars": 0.0,
    "review_mgmt": 0.0,
    "packaging": 0.0,
    "dropoff": 0.0,
    "other_fees": 0.0,
    "revenue_return": 0.0,
    "commission_return": 0.0,
    "total_amount": 0.0,
    "n_ops": 0,
})

TYPE_MAP = {
    "Выручка": "revenue",
    "Баллы за скидки": "loyalty_points",
    "Программы партнёров": "partner_programs",
    "Вознаграждение за продажу": "commission",
    "Возврат вознаграждения": "commission_return",
    "Возврат выручки": "revenue_return",
    "Логистика": "logistics",
    "Доставка до места выдачи": "last_mile",
    "Доставка до места выдачи силами Ozon": "last_mile",
    "Эквайринг": "acquiring",
    "Обратная логистика": "reverse_logistics",
    "Обработка возвратов, отмен и невыкупов партнёрами": "returns_fee",
    "Подписка Premium Pro (процент)": "premium",
    "Звёздные товары": "stars",
    "Подписка Управление отзывами": "review_mgmt",
    "Упаковка товара партнёрами": "packaging",
    "Обеспечение материалами для упаковки товара": "packaging",
    "Обработка отправления Drop-off (СЦ)": "dropoff",
}

for c in charges:
    o = c["offer_id"]
    a = agg[o]
    a["name"] = c["name"] or a["name"]
    a["n_ops"] += 1
    a["total_amount"] += c["amount"]
    key = TYPE_MAP.get(c["type"], "other_fees")
    a[key] += c["amount"]
    if c["type"] == "Выручка":
        a["qty_sold"] += c["qty"] or 0

# print summary totals
keys = ["qty_sold","revenue","loyalty_points","partner_programs","commission","commission_return",
        "revenue_return","logistics","last_mile","acquiring","reverse_logistics","returns_fee",
        "premium","stars","review_mgmt","packaging","dropoff","other_fees","total_amount"]
tot = {k: sum(a[k] for a in agg.values()) for k in keys}
print("\n=== TOTALS ===")
for k in keys:
    print(f"{k:22s} {tot[k]:12.2f}")

print("\n=== commission/revenue ratio ===")
if tot["revenue"]:
    print("commission % of revenue", round(tot["commission"]/tot["revenue"]*100, 2))
    print("all fees % of revenue", round((tot["revenue"]-tot["total_amount"])/tot["revenue"]*100, 2) if tot["revenue"] else None)

print("\n=== top 15 SKUs by revenue ===")
top = sorted(agg.items(), key=lambda x: -x[1]["revenue"])[:15]
for o, a in top:
    fees = a["revenue"] - (a["revenue"] + a["commission"] + a["logistics"] + a["last_mile"] + a["acquiring"])
    # actual payout = total_amount (sum of all signed amounts)
    ozon_take_pct = (-(a["commission"] + a["logistics"] + a["last_mile"] + a["acquiring"] + a["reverse_logistics"] +
                       a["returns_fee"] + a["premium"] + a["stars"] + a["review_mgmt"] + a["packaging"] + a["dropoff"] +
                       a["other_fees"]) / a["revenue"] * 100) if a["revenue"] else 0
    print(f"{o:20s} qty={a['qty_sold']:4.0f} rev={a['revenue']:10.2f} comm={a['commission']:10.2f} "
          f"log={a['logistics']:8.2f} payout={a['total_amount']:10.2f} ozon_take%={ozon_take_pct:5.1f} "
          f"{a['name'][:40]}")

# save agg
out = {o: a for o, a in agg.items()}
json.dump(out, open(r"C:\Users\Alex\ozon_analytics\sku_agg_raw.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("\nsaved sku_agg", len(out))
