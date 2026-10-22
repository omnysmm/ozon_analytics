"""Compute recommended Ozon price to hit clean margin K from price list column K."""
import json
from pathlib import Path

OUT = Path(r"C:\Users\Alex\ozon_analytics")
web = json.load(open(OUT / "website_data.json", encoding="utf-8"))
econ = web["sku_economics"]


def recommend_ozon_price(row):
    """price - commission - other_ozon_costs - cost = K
    commission ≈ comm_rate * price
    other_ozon ≈ other_unit (logistics, last mile, services per unit)
    => price = (cost + K + other_unit) / (1 - comm_rate)
    """
    cost = row.get("cost_rub")
    target_margin = row.get("required_markup")  # column K
    if cost is None:
        return None

    qty = max(row.get("qty_sold") or 1, 1)
    gross = row.get("gross_product") or 0
    total_fees = abs(row.get("total_fees") or 0)
    commission = abs(row.get("commission") or 0)

    # commission rate from actual charges
    if gross > 0 and commission > 0:
        comm_rate = commission / gross
    elif row.get("avg_reward_pct_actual"):
        comm_rate = row["avg_reward_pct_actual"] / 100.0
    elif row.get("api_sales_percent"):
        comm_rate = row["api_sales_percent"] / 100.0
    else:
        comm_rate = 0.50

    # other ozon costs per unit (logistics etc, excluding sales commission)
    if gross > 0 and total_fees > 0:
        other_unit = max(total_fees - commission, 0) / qty
    elif row.get("ozon_fee_plan") is not None:
        # plan P includes commission+logistics — estimate other as P minus comm on avg price
        plan = row["ozon_fee_plan"]
        avg_price = gross / qty if gross else (row.get("price_ozon") or 0)
        est_comm = comm_rate * avg_price
        other_unit = max(plan - est_comm, plan * 0.35)
    else:
        other_unit = max((row.get("logistics") or 0) / qty, 20)

    k = target_margin if target_margin is not None else 0.0
    denom = 1.0 - comm_rate
    if denom <= 0.05:
        denom = 0.5

    price = (cost + k + other_unit) / denom

    # sanity: also provide variant using only plan P (sheet-native)
    plan_p = row.get("ozon_fee_plan")
    price_simple = (cost + k + plan_p) if plan_p is not None else None

    # expected payout and check
    expected_comm = comm_rate * price
    expected_payout = price - expected_comm - other_unit
    expected_profit = expected_payout - cost

    return {
        "price_rec": round(price, 0),
        "price_rec_simple_jkP": round(price_simple, 0) if price_simple else None,
        "target_margin_k": k,
        "cost_j": cost,
        "comm_rate": round(comm_rate * 100, 2),
        "other_unit": round(other_unit, 2),
        "expected_payout": round(expected_payout, 2),
        "expected_profit": round(expected_profit, 2),
        "formula": "(J + K + прочие_затраты_Ozon) / (1 − комиссия%)",
    }


n = 0
for row in econ:
    rec = recommend_ozon_price(row)
    if not rec:
        row["price_rec_for_margin_k"] = None
        continue
    n += 1
    row["price_rec_for_margin_k"] = rec["price_rec"]
    row["price_rec_simple_jkP"] = rec["price_rec_simple_jkP"]
    row["target_margin_k"] = rec["target_margin_k"]
    row["comm_rate_pct"] = rec["comm_rate"]
    row["ozon_other_unit"] = rec["other_unit"]
    row["expected_payout_rec"] = rec["expected_payout"]
    row["expected_profit_rec"] = rec["expected_profit"]

# refresh recs: include margin-K price as the primary suggested price when K present
recs = web.get("price_recommendations") or []
rec_by_offer = {r["offer_id"]: r for r in recs}
for row in econ:
    r = rec_by_offer.get(row["offer_id"])
    if r is not None:
        r["price_rec_for_margin_k"] = row.get("price_rec_for_margin_k")
        r["target_margin_k"] = row.get("target_margin_k")
        r["comm_rate_pct"] = row.get("comm_rate_pct")
        r["ozon_other_unit"] = row.get("ozon_other_unit")
        r["expected_profit_rec"] = row.get("expected_profit_rec")
        # preferred action price = price that yields margin K
        if row.get("price_rec_for_margin_k"):
            r["suggested_price"] = row["price_rec_for_margin_k"]
            if row.get("required_markup") is not None:
                r["reason"] = (r.get("reason") or "") + f"; цена под целевую маржу K={row['required_markup']:.0f} ₽"

web["sku_economics"] = econ
web["price_recommendations"] = list(rec_by_offer.values())
web["price_rec_formula"] = {
    "target": "чистая маржа = K (столбец «Необходимая наценка»)",
    "formula": "Цена = (Себестоимость J + Маржа K + прочие затраты Ozon/шт) / (1 − комиссия%)",
    "comm_rate": "из фактических начислений Ozon (Вознаграждение / выручка)",
    "other_unit": "логистика, последняя миля, сервисы — из факта, без комиссии",
}

json.dump(web, open(OUT / "website_data.json", "w", encoding="utf-8"), ensure_ascii=False)

print("with price_rec", n)
print("formula", web["price_rec_formula"])
print("\nsamples:")
for r in econ[:8]:
    print(
        f"{r['offer_id']:16s} J={r.get('cost_rub')} K={r.get('required_markup')} "
        f"price_ozon={r.get('price_ozon')} rec={r.get('price_rec_for_margin_k')} "
        f"comm%={r.get('comm_rate_pct')} other={r.get('ozon_other_unit')} "
        f"profit={r.get('expected_profit_rec')}"
    )
