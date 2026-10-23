"""Unify current price = live Ozon API; add competitor source labels; rebuild recs."""
import json
from pathlib import Path

OUT = Path(r"C:\Users\Alex\ozon_analytics")

live = json.load(open(OUT / "ozon_live_prices.json", encoding="utf-8"))
prices = json.load(open(OUT / "ozon_prices_full.json", encoding="utf-8"))
web = json.load(open(OUT / "website_data.json", encoding="utf-8"))
econ = web["sku_economics"]

price_idx = {p["offer_id"]: p for p in prices}

# Competitor source labeling from Ozon price_indexes
# external_index_data = min price on external marketplaces (WB/YM/Avito...)
# self_marketplaces_index_data = min price among other sellers ON Ozon
# ozon_index_data = Ozon Retail

def competitor_fields(offer, row):
    p = price_idx.get(offer) or {}
    idx = p.get("price_indexes") or {}
    ext = idx.get("external_index_data") or {}
    self_mp = idx.get("self_marketplaces_index_data") or {}
    ozon_i = idx.get("ozon_index_data") or {}

    candidates = []
    if ext.get("min_price"):
        candidates.append({
            "price": ext.get("min_price"),
            "source_code": "external_mp",
            "source_label": "Внешние МП (Ozon индекс)",
            "seller": "Конкурент на WB / Я.Маркет / др. МП",
            "index_value": ext.get("price_index_value"),
            "index_color": ext.get("price_index_color"),
        })
    if self_mp.get("min_price"):
        candidates.append({
            "price": self_mp.get("min_price"),
            "source_code": "ozon_sellers",
            "source_label": "Другие продавцы на Ozon",
            "seller": "Продавец Ozon (min price, имя не раскрывается API)",
            "index_value": self_mp.get("price_index_value"),
            "index_color": self_mp.get("price_index_color"),
        })
    if ozon_i.get("min_price"):
        candidates.append({
            "price": ozon_i.get("min_price"),
            "source_code": "ozon_retail",
            "source_label": "Ozon Retail",
            "seller": "Ozon Retail",
            "index_value": ozon_i.get("price_index_value"),
            "index_color": ozon_i.get("price_index_color"),
        })

    # pick cheapest competitor
    best = None
    for c in candidates:
        if c["price"] and (best is None or c["price"] < best["price"]):
            best = c
    return best, candidates


for row in econ:
    offer = row.get("offer_id")
    lp = live.get(offer) or {}
    # CURRENT price must be from Ozon
    row["price_ozon"] = lp.get("price_ozon") or row.get("seller_price_api")
    row["min_price_ozon"] = lp.get("min_price_ozon") or row.get("min_price")
    row["old_price_ozon"] = lp.get("old_price_ozon") or row.get("old_price")
    row["price_source"] = "Ozon API /v3/product/info/list"
    # keep avg sale for reference but DO NOT show as current
    qty = max(row.get("qty_sold") or 1, 1)
    row["avg_sale_price"] = round((row.get("gross_product") or 0) / qty, 2)

    best, allc = competitor_fields(offer, row)
    if best:
        row["competitor_price"] = best["price"]
        row["competitor_seller"] = best["seller"]
        row["competitor_source"] = best["source_label"]
        row["competitor_source_code"] = best["source_code"]
        row["price_index_value"] = best.get("index_value")
        row["price_index_color"] = best.get("index_color") or row.get("price_index_color")
    else:
        # fallback: min of external/ozon if any stored
        alt = row.get("competitor_min_external") or row.get("competitor_min_ozon")
        row["competitor_price"] = alt
        row["competitor_seller"] = "Не определён" if not alt else "Ozon индекс (min)"
        row["competitor_source"] = "Нет данных индекса" if not alt else "Ozon индекс (min)"
        row["competitor_source_code"] = "none"
    row["competitor_all"] = allc
    # compact multi-line display: price + source for EVERY index (not just min)
    lines = []
    for c in sorted(allc, key=lambda x: x.get("price") or 0):
        if not c.get("price"):
            continue
        lines.append(f"{c['price']:.0f} ₽ · {c['source_label']}")
    row["competitor_display"] = "\n".join(lines) if lines else "—"

# rebuild recommendations with price_ozon as current
recs = []
for r in econ:
    qty = r.get("qty_sold") or 0
    profit = r.get("profit_unit")
    is_loss = profit is not None and profit <= 0
    # qty>=5 is enough for price recs; unprofitable SKUs always included
    # so «Убыточные» filter matches the costs tab
    if qty < 5 and not is_loss:
        continue
    price = r.get("price_ozon") or r.get("avg_sale_price") or 0
    payout_u = (r.get("payout") or 0) / max(r.get("qty_sold") or 1, 1)
    take = r.get("ozon_take_pct") or 0
    cost = r.get("cost_rub")
    comp = r.get("competitor_price")
    comp_seller = r.get("competitor_seller")
    comp_src = r.get("competitor_source")

    action = "УДЕРЖАТЬ"
    reason = f"Ozon забирает {take:.0f}%"
    sug = round(price, 0) if price else None

    if take >= 70:
        action = "ПОВЫСИТЬ"
        reason = f"Ozon забирает {take:.0f}% — маржа подавлена"
        sug = round(price * 1.12, 0) if price else None
    elif take <= 45:
        action = "СНИЗИТЬ/УДЕРЖАТЬ"
        reason = f"Ozon забирает {take:.0f}% — есть запас"
        sug = round(price * 0.95, 0) if price else None

    if cost is not None and payout_u is not None and payout_u < cost:
        action = "ПОВЫСИТЬ"
        reason = f"Выплата {payout_u:.0f} ₽ < себестоимости {cost:.0f} ₽"
        sug = round(max(price or 0, (cost + (r.get('total_fees') or 0) / max(r.get('qty_sold') or 1, 1)) * 1.1), 0)

    if comp and price:
        gap = (price - comp) / comp * 100
        if price > comp * 1.15:
            action = "СНИЗИТЬ"
            reason = reason + f"; наша цена выше конкурента на {gap:.1f}%"
            sug = round(min(sug or price, comp * 1.05), 0)
        elif price < comp * 0.85 and take < 55:
            action = "ПОВЫСИТЬ"
            reason = reason + f"; наша цена ниже конкурента на {abs(gap):.1f}%"
            sug = round(comp * 0.95, 0)

    recs.append({
        "offer_id": r["offer_id"],
        "name": r.get("name"),
        "qty_sold": r.get("qty_sold"),
        "current_price_ozon": price,
        "current_price_source": "Ozon API",
        "avg_sale_price": r.get("avg_sale_price"),
        "cost_rub": cost,
        "competitor_price": comp,
        "competitor_seller": comp_seller,
        "competitor_source": comp_src,
        "competitor_display": r.get("competitor_display"),
        "competitor_all": r.get("competitor_all") or [],
        "ozon_take_pct": take,
        "payout_per_unit": round(payout_u, 2),
        "profit_unit": r.get("profit_unit"),
        "margin_on_payout_pct": r.get("margin_on_payout_pct"),
        "ozon_fee_plan": r.get("ozon_fee_plan"),
        "ozon_fee_actual_unit": r.get("ozon_fee_actual_unit"),
        "ozon_fee_diff": r.get("ozon_fee_diff"),
        "action": action,
        "suggested_price": sug,
        "reason": reason,
    })

web["sku_economics"] = econ
web["price_recommendations"] = recs
web["price_fields_note"] = {
    "current_price": "price_ozon из Ozon API /v3/product/info/list",
    "avg_sale_price": "средняя фактическая цена продажи (выручка/кол-во), справочно",
    "competitor_price": "min price из price_indexes Ozon API",
    "competitor_seller": "источник/подпись источника цены конкурента",
}
json.dump(web, open(OUT / "website_data.json", "w", encoding="utf-8"), ensure_ascii=False)

# stats
print("sku", len(econ), "recs", len(recs))
print("with price_ozon", sum(1 for r in econ if r.get("price_ozon")))
print("with competitor_price", sum(1 for r in econ if r.get("competitor_price")))
print("competitor sources:")
from collections import Counter
print(Counter(r.get("competitor_source") for r in econ))
print("sample NK5415:")
r = next(x for x in econ if x["offer_id"] == "NK5415")
for k in ["price_ozon", "avg_sale_price", "competitor_price", "competitor_seller", "competitor_source", "min_price_ozon", "old_price_ozon"]:
    print(" ", k, r.get(k))
print("recs actions", Counter(x["action"] for x in recs))
