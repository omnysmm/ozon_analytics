"""Assemble all data into website payload: economics, analytics, costs, WB comparison, recs."""
import json
import openpyxl
from collections import defaultdict
from pathlib import Path

OUT = Path(r"C:\Users\Alex\ozon_analytics")

# ---------- load core ----------
econ = json.load(open(OUT / "sku_economics.json", encoding="utf-8"))
totals = json.load(open(OUT / "totals.json", encoding="utf-8"))
analytics_skus = json.load(open(OUT / "analytics_skus.json", encoding="utf-8"))
analytics_days = json.load(open(OUT / "analytics_days.json", encoding="utf-8"))
prices = json.load(open(OUT / "ozon_prices_full.json", encoding="utf-8"))

price_by_offer = {p["offer_id"]: p for p in prices}

# analytics by sku id (Ozon SKU)
an_by_sku = {}
for row in analytics_skus:
    dim = (row.get("dimensions") or [{}])[0]
    sku = str(dim.get("id"))
    m = row.get("metrics") or [0, 0, 0, 0, 0]
    an_by_sku[sku] = {
        "revenue": m[0] if len(m) > 0 else 0,
        "ordered_units": m[1] if len(m) > 1 else 0,
        "returns": m[2] if len(m) > 2 else 0,
        "cancellations": m[3] if len(m) > 3 else 0,
        "views": m[4] if len(m) > 4 else 0,
        "name": dim.get("name") or "",
    }

# days
days = []
for row in analytics_days:
    dim = (row.get("dimensions") or [{}])[0]
    m = row.get("metrics") or [0, 0, 0, 0, 0]
    days.append({
        "date": dim.get("id"),
        "revenue": m[0] if len(m) > 0 else 0,
        "ordered_units": m[1] if len(m) > 1 else 0,
        "returns": m[2] if len(m) > 2 else 0,
        "cancellations": m[3] if len(m) > 3 else 0,
        "views": m[4] if len(m) > 4 else 0,
    })
days.sort(key=lambda d: d["date"])

# ---------- WB costs from local xlsx ----------
wb_costs = []
try:
    wb = openpyxl.load_workbook(r"C:\Users\Alex\Yandex.Disk\Pugovicnet\Цены фурнитура ВБ.xlsx", data_only=True, read_only=True)
    ws = wb["Лист1"]
    rows = list(ws.iter_rows(values_only=True))
    wb.close()
    header = rows[0]
    for r in rows[1:]:
        if not r or not r[1]:
            continue
        wb_costs.append({
            "name": r[1],
            "qty": r[2],
            "unit": r[3],
            "unit_cost_foreign": r[4],
            "sum_foreign": r[5],
            "delivery": r[6],
            "wb_tax_pct": r[7],
            "markup_price": r[8],          # цена продажи / наценка
            "cost_rub": r[9],              # себестоимость
            "pack_logistics": r[10],
            "min_comp_price": r[11],
            "usd_rate": r[12],             # 75
            "profit_rub": r[13],
            "profit_pct": r[14],
        })
except Exception as e:
    print("wb costs err", e)

# ---------- supplier price list ----------
supplier = []
try:
    wb = openpyxl.load_workbook(r"C:\Users\Alex\Yandex.Disk\Загрузки\Копия запрос по ценам3 .xlsx", data_only=True, read_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    wb.close()
    for r in rows[1:]:
        if not r or not r[1]:
            continue
        supplier.append({
            "name": r[0],
            "offer": r[1],
            "qty": r[2],
            "qty2": r[3],
            "price": r[4],
            "discount_pct": r[5],
            "sum": r[6],
        })
except Exception as e:
    print("supplier err", e)

# ---------- 1C retail prices ----------
retail = {}
try:
    wb = openpyxl.load_workbook(r"C:\Users\Alex\Yandex.Disk\Pugovicnet\прайс для 1С.xlsx", data_only=True, read_only=True)
    ws = wb["Общий отчет"]
    rows = list(ws.iter_rows(values_only=True))
    wb.close()
    for r in rows[1:]:
        if not r or not r[5]:
            continue
        retail[str(r[5])] = {
            "retail": r[0],
            "discount_site_pct": r[1],
            "wb_price": r[2],
            "site_price": r[3],
            "offer": r[5],
            "barcode": r[6],
        }
except Exception as e:
    print("retail err", e)

# ---------- enrich economics + price recommendations ----------
def recommend(row, comp_min=None):
    """Price recommendation based on payout, take %, competitor min."""
    gross = row.get("gross_product") or 0
    qty = max(row.get("qty_sold") or 1, 1)
    avg_price = gross / qty if qty else 0
    payout_unit = (row.get("payout") or 0) / qty
    take_pct = row.get("ozon_take_pct") or 60
    # target: seller wants at least 25% of avg_price as payout margin over unknown COGS
    # recommendation relative to current avg price
    api_price = row.get("seller_price_api") or avg_price
    rec = {
        "current_avg_price": round(avg_price, 2),
        "api_price": api_price,
        "payout_per_unit": round(payout_unit, 2),
        "ozon_take_pct": take_pct,
    }
    if comp_min and comp_min > 0:
        rec["competitor_min"] = comp_min
        rec["price_gap_pct"] = round((avg_price - comp_min) / comp_min * 100, 1)
    # if take% > 70 and payout low → raise price; if far above competitor → lower
    if take_pct >= 70:
        rec["action"] = "ПОВЫСИТЬ"
        rec["reason"] = f"Ozon забирает {take_pct:.0f}% — маржа подавлена"
        rec["suggested_price"] = round(avg_price * 1.12, 0)
    elif take_pct <= 45:
        rec["action"] = "СНИЗИТЬ/УДЕРЖАТЬ"
        rec["reason"] = f"Ozon забирает {take_pct:.0f}% — есть запас на демпинг"
        rec["suggested_price"] = round(avg_price * 0.95, 0)
    else:
        rec["action"] = "УДЕРЖАТЬ"
        rec["reason"] = f"Ozon забирает {take_pct:.0f}% — сбалансировано"
        rec["suggested_price"] = round(avg_price, 0)
    if comp_min and avg_price > comp_min * 1.15:
        rec["action"] = "СНИЗИТЬ"
        rec["reason"] = (rec.get("reason") or "") + f"; цена выше конкурента на {rec['price_gap_pct']}%"
        rec["suggested_price"] = round(min(rec["suggested_price"], comp_min * 1.05), 0)
    elif comp_min and avg_price < comp_min * 0.85 and take_pct < 55:
        rec["action"] = "ПОВЫСИТЬ"
        rec["reason"] = (rec.get("reason") or "") + f"; цена ниже конкурента на {abs(rec.get('price_gap_pct',0)):.0f}%"
        rec["suggested_price"] = round(comp_min * 0.95, 0)
    return rec

enriched = []
for row in econ:
    sku = str(row.get("sku") or "")
    an = an_by_sku.get(sku, {})
    pr = price_by_offer.get(row["offer_id"], {})
    idx = pr.get("price_indexes") or {}
    ext = idx.get("external_index_data") or {}
    self_mp = idx.get("self_marketplaces_index_data") or {}
    comp_min = ext.get("min_price") or self_mp.get("min_price") or row.get("competitor_min_external") or row.get("competitor_min_ozon")
    rec = recommend(row, comp_min)
    r = dict(row)
    r["analytics"] = an
    r["price_recommendation"] = rec
    r["competitor_min_external"] = ext.get("min_price")
    r["competitor_min_ozon"] = self_mp.get("min_price")
    r["price_index_color"] = idx.get("color_index") or ext.get("price_index_color")
    r["price_index_value"] = ext.get("price_index_value")
    r["old_price"] = (pr.get("price") or {}).get("old_price") or row.get("old_price")
    r["seller_price_api"] = (pr.get("price") or {}).get("price") or row.get("seller_price_api")
    # cost matching by name (best-effort)
    name_l = (r.get("name") or "").lower()
    cost_guess = None
    for wc in wb_costs:
        if wc.get("name") and str(wc["name"]).lower()[:20] in name_l:
            cost_guess = wc.get("cost_rub")
            break
    r["cost_rub_guess"] = cost_guess
    if cost_guess:
        qty = max(r.get("qty_sold") or 1, 1)
        payout_unit = (r.get("payout") or 0) / qty
        r["profit_unit_guess"] = round(payout_unit - cost_guess, 2)
        r["margin_pct_guess"] = round((payout_unit - cost_guess) / payout_unit * 100, 1) if payout_unit else None
    enriched.append(r)

# ---------- fee structure for charts ----------
fee_totals = defaultdict(float)
for r in econ:
    for k in ["commission", "logistics", "last_mile", "acquiring", "reverse_logistics",
              "premium", "stars", "review_mgmt", "packaging", "dropoff", "returns_fee", "first_reviews", "other_fees"]:
        fee_totals[k] += abs(r.get(k) or 0)
fee_totals = dict(fee_totals)

# ---------- WB vs Ozon comparison ----------
ozon_summary = {
    "period": "2026-09-14 — 2026-10-14",
    "gross_product": totals["gross_product"],
    "total_fees": totals["total_fees"],
    "payout": totals["payout"],
    "ozon_take_pct": totals["ozon_take_pct"],
    "payout_pct": totals["payout_pct"],
    "qty_sold": totals["qty_sold"],
    "skus_sold": totals["skus_sold"],
    "avg_take_pct": round(sum(r["ozon_take_pct"] or 0 for r in econ) / max(len(econ), 1), 2),
    "commission_pct": round(fee_totals.get("commission", 0) / totals["gross_product"] * 100, 2),
    "logistics_pct": round(fee_totals.get("logistics", 0) / totals["gross_product"] * 100, 2),
    "other_fees_pct": round((totals["total_fees"] - fee_totals.get("commission", 0) - fee_totals.get("logistics", 0)) / totals["gross_product"] * 100, 2),
}

# WB model from local sheet: typical wb take is ~15-25% (commission+logistics+tax)
wb_summary = {
    "source": "Цены фурнитура ВБ.xlsx (плановые)",
    "note": "Локальная таблица; API/отчёты WB не подключены",
    "avg_cost_rub": None,
    "avg_markup_price": None,
    "avg_min_comp": None,
    "avg_profit_pct": None,
    "assumed_wb_take_pct": 20,
}
if wb_costs:
    def avg(key):
        vals = [c[key] for c in wb_costs if isinstance(c.get(key), (int, float))]
        return round(sum(vals) / len(vals), 2) if vals else None
    wb_summary["avg_cost_rub"] = avg("cost_rub")
    wb_summary["avg_markup_price"] = avg("markup_price")
    wb_summary["avg_min_comp"] = avg("min_comp_price")
    wb_summary["avg_profit_pct"] = avg("profit_pct")
    wb_summary["n_items"] = len(wb_costs)

comparison = {
    "ozon": ozon_summary,
    "wb": wb_summary,
    "delta_take_pct": round(ozon_summary["ozon_take_pct"] - wb_summary["assumed_wb_take_pct"], 2),
    "verdict": (
        f"Ozon забирает ~{ozon_summary['ozon_take_pct']}% выручки (комиссия ~{ozon_summary['commission_pct']}% + логистика и сервисы). "
        f"На WB по плановой модели расходы ~{wb_summary['assumed_wb_take_pct']}% (комиссия+логистика+налоги). "
        f"Разница ≈ {round(ozon_summary['ozon_take_pct'] - wb_summary['assumed_wb_take_pct'],1)} п.п. в пользу WB."
    ),
}

payload = {
    "generated_at": "2026-10-22",
    "period": ozon_summary["period"],
    "totals": totals,
    "fee_totals": fee_totals,
    "fee_pct": {k: round(v / totals["gross_product"] * 100, 2) for k, v in fee_totals.items()},
    "sku_economics": enriched[:400],  # top 400 for page weight
    "sku_economics_count": len(enriched),
    "days": days,
    "wb_costs": wb_costs,
    "supplier_prices": supplier[:200],
    "retail_prices": retail,
    "comparison": comparison,
    "price_recommendations": [
        {
            "offer_id": r["offer_id"],
            "name": r["name"],
            "qty_sold": r["qty_sold"],
            "ozon_take_pct": r["ozon_take_pct"],
            "current_avg_price": r["price_recommendation"]["current_avg_price"],
            "suggested_price": r["price_recommendation"].get("suggested_price"),
            "action": r["price_recommendation"].get("action"),
            "reason": r["price_recommendation"].get("reason"),
            "payout_per_unit": r["price_recommendation"].get("payout_per_unit"),
            "competitor_min": r["price_recommendation"].get("competitor_min"),
        }
        for r in enriched
        if r.get("qty_sold", 0) >= 5
    ],
}

json.dump(payload, open(OUT / "website_data.json", "w", encoding="utf-8"), ensure_ascii=False)
print("payload keys", payload.keys())
print("fee_pct", payload["fee_pct"])
print("comparison", comparison["verdict"])
print("recs", len(payload["price_recommendations"]))
print("sku rows", len(enriched), "saved top", len(payload["sku_economics"]))
print("wb_costs", len(wb_costs), "supplier", len(supplier), "retail", len(retail))
print("days", len(days))
