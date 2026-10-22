"""Build unified per-SKU Ozon economics from charges + realization + prices."""
import json
from collections import defaultdict
from pathlib import Path

OUT = Path(r"C:\Users\Alex\ozon_analytics")

charges = json.load(open(OUT / "charges_raw.json", encoding="utf-8"))
prices = json.load(open(OUT / "ozon_prices_full.json", encoding="utf-8"))
products_list = json.load(open(OUT / "ozon_products_list.json", encoding="utf-8"))

price_by_offer = {}
for p in prices:
    price_by_offer[p["offer_id"]] = p

list_by_offer = {p["offer_id"]: p for p in products_list}

# ---- aggregate charges per offer_id ----
# Economic model (verified):
#   seller_price ≈ revenue + loyalty_points + partner_programs
#   commission = seller_price * reward_pct  (type «Вознаграждение за продажу»)
#   payout = sum of all signed amounts
agg = defaultdict(lambda: {
    "offer_id": "",
    "sku": "",
    "name": "",
    "qty_sold": 0,
    "qty_returned": 0,
    "revenue": 0.0,
    "loyalty_points": 0.0,
    "partner_programs": 0.0,
    "gross_product": 0.0,          # revenue + loyalty + partner (≈ seller price * qty)
    "commission": 0.0,             # negative
    "commission_return": 0.0,
    "revenue_return": 0.0,
    "logistics": 0.0,
    "last_mile": 0.0,
    "acquiring": 0.0,
    "reverse_logistics": 0.0,
    "returns_fee": 0.0,
    "premium": 0.0,
    "stars": 0.0,
    "review_mgmt": 0.0,
    "packaging": 0.0,
    "dropoff": 0.0,
    "first_reviews": 0.0,
    "other_fees": 0.0,
    "payout": 0.0,                 # sum of all signed amounts
    "n_ops": 0,
    "reward_pcts": [],
    "schemes": set(),
})

FEE_KEYS = [
    "commission", "logistics", "last_mile", "acquiring", "reverse_logistics",
    "returns_fee", "premium", "stars", "review_mgmt", "packaging", "dropoff",
    "first_reviews", "other_fees",
]

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
    "Сбор первых отзывов": "first_reviews",
    "Вывоз товара со склада силами Ozon: Доставка до ПВЗ": "other_fees",
    "Подготовка товара к вывозу: Валид": "other_fees",
    "Подготовка товара к вывозу: Брак": "other_fees",
    "Временное размещение товара партнерами": "other_fees",
}

for c in charges:
    o = c["offer_id"]
    a = agg[o]
    a["offer_id"] = o
    a["sku"] = str(c.get("sku") or a["sku"])
    a["name"] = c.get("name") or a["name"]
    a["n_ops"] += 1
    a["payout"] += c["amount"]
    if c.get("scheme"):
        a["schemes"].add(c["scheme"])
    if c.get("reward_pct") not in (None, 0, 0.0):
        a["reward_pcts"].append(float(c["reward_pct"]))
    key = TYPE_MAP.get(c["type"], "other_fees")
    a[key] += c["amount"]
    if c["type"] == "Выручка":
        a["qty_sold"] += c["qty"] or 0
    if c["type"] == "Возврат выручки":
        a["qty_returned"] += c["qty"] or 0

# enrich with catalog prices and commissions from API
rows = []
for o, a in agg.items():
    pr = price_by_offer.get(o, {})
    price_obj = pr.get("price") or {}
    comm = pr.get("commissions") or {}
    idx = pr.get("price_indexes") or {}
    ext = idx.get("external_index_data") or {}
    self_mp = idx.get("self_marketplaces_index_data") or {}
    ozon_idx = idx.get("ozon_index_data") or {}

    seller_price = price_obj.get("price") or 0
    old_price = price_obj.get("old_price") or 0
    min_price = price_obj.get("min_price") or 0
    vat = price_obj.get("vat")
    acquiring_pct = pr.get("acquiring")

    gross = a["revenue"] + a["loyalty_points"] + a["partner_programs"]
    total_fees = -sum(a[k] for k in FEE_KEYS)  # positive number = fees
    # note: commission is already negative in a["commission"]
    fees_abs = sum(abs(a[k]) for k in FEE_KEYS if a[k] < 0)
    # refunds net
    net_after_refunds = a["payout"]

    ozon_take_pct = (fees_abs / gross * 100) if gross > 0 else None
    payout_pct = (a["payout"] / gross * 100) if gross > 0 else None

    avg_reward = (sum(a["reward_pcts"]) / len(a["reward_pcts"])) if a["reward_pcts"] else None
    api_sales_pct = comm.get("sales_percent_fbs") or comm.get("sales_percent_fbo")

    row = {
        "offer_id": o,
        "sku": a["sku"],
        "name": a["name"],
        "qty_sold": a["qty_sold"],
        "qty_returned": a["qty_returned"],
        "seller_price_api": seller_price,
        "old_price": old_price,
        "min_price": min_price,
        "vat": vat,
        "acquiring_pct_api": acquiring_pct,
        "api_sales_percent": api_sales_pct,
        "avg_reward_pct_actual": round(avg_reward * 100, 2) if avg_reward is not None else None,
        "gross_product": round(gross, 2),
        "revenue_cash": round(a["revenue"], 2),
        "loyalty_points": round(a["loyalty_points"], 2),
        "partner_programs": round(a["partner_programs"], 2),
        "commission": round(a["commission"], 2),
        "commission_return": round(a["commission_return"], 2),
        "revenue_return": round(a["revenue_return"], 2),
        "logistics": round(a["logistics"], 2),
        "last_mile": round(a["last_mile"], 2),
        "acquiring": round(a["acquiring"], 2),
        "reverse_logistics": round(a["reverse_logistics"], 2),
        "returns_fee": round(a["returns_fee"], 2),
        "premium": round(a["premium"], 2),
        "stars": round(a["stars"], 2),
        "review_mgmt": round(a["review_mgmt"], 2),
        "packaging": round(a["packaging"], 2),
        "dropoff": round(a["dropoff"], 2),
        "first_reviews": round(a["first_reviews"], 2),
        "other_fees": round(a["other_fees"], 2),
        "total_fees": round(fees_abs, 2),
        "payout": round(a["payout"], 2),
        "ozon_take_pct": round(ozon_take_pct, 2) if ozon_take_pct is not None else None,
        "payout_pct": round(payout_pct, 2) if payout_pct is not None else None,
        "fbo_log_min": comm.get("fbs_direct_flow_trans_min_amount") or comm.get("fbo_direct_flow_trans_min_amount"),
        "fbo_log_max": comm.get("fbs_direct_flow_trans_max_amount") or comm.get("fbo_direct_flow_trans_max_amount"),
        "competitor_min_external": ext.get("min_price"),
        "competitor_min_ozon": self_mp.get("min_price"),
        "price_index_color": idx.get("color_index") or ext.get("price_index_color"),
        "price_index_value": ext.get("price_index_value"),
        "n_ops": a["n_ops"],
        "schemes": ",".join(sorted(a["schemes"])),
    }
    rows.append(row)

# sort by gross desc
rows.sort(key=lambda r: -r["gross_product"])

# totals
def s(k):
    return sum(r[k] or 0 for r in rows)

totals = {
    "skus_sold": len(rows),
    "qty_sold": s("qty_sold"),
    "gross_product": round(s("gross_product"), 2),
    "revenue_cash": round(s("revenue_cash"), 2),
    "loyalty_points": round(s("loyalty_points"), 2),
    "commission": round(s("commission"), 2),
    "logistics": round(s("logistics"), 2),
    "last_mile": round(s("last_mile"), 2),
    "acquiring": round(s("acquiring"), 2),
    "reverse_logistics": round(s("reverse_logistics"), 2),
    "premium": round(s("premium"), 2),
    "stars": round(s("stars"), 2),
    "review_mgmt": round(s("review_mgmt"), 2),
    "total_fees": round(s("total_fees"), 2),
    "payout": round(s("payout"), 2),
}
totals["ozon_take_pct"] = round(totals["total_fees"] / totals["gross_product"] * 100, 2)
totals["payout_pct"] = round(totals["payout"] / totals["gross_product"] * 100, 2)

print("=== TOTALS ===")
for k, v in totals.items():
    print(f"{k:22s} {v}")

print("\n=== TOP 12 ===")
for r in rows[:12]:
    print(f"{r['offer_id']:18s} qty={r['qty_sold']:4.0f} gross={r['gross_product']:10.2f} "
          f"fees={r['total_fees']:9.2f} take%={r['ozon_take_pct']} payout={r['payout']:9.2f} "
          f"comm%={r['avg_reward_pct_actual']} {r['name'][:36]}")

json.dump(rows, open(OUT / "sku_economics.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(totals, open(OUT / "totals.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("\nsaved sku_economics", len(rows))
