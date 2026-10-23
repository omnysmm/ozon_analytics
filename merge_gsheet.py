"""Full parse of Google Sheet + merge with Ozon economics + plan vs fact."""
import csv
import json
import re
from pathlib import Path

OUT = Path(r"C:\Users\Alex\ozon_analytics")


def to_num(v):
    if v is None:
        return None
    s = str(v).strip().replace("\xa0", "").replace(" ", "").replace("%", "").replace(",", ".")
    if s == "" or s.lower() in ("none", "-", "—"):
        return None
    try:
        return float(s)
    except Exception:
        return None


rows = list(csv.reader((OUT / "gsheet.csv").read_text(encoding="utf-8-sig").splitlines()))
header = rows[0]
data_rows = rows[1:]

# columns: A=id?, B=name, C=offer, J=cost, P=ozon_plan, R=ozon_price, X=retail, L=wb, N=wb_price, Y=margin
catalog = {}
for r in data_rows:
    if len(r) < 16:
        continue
    name = (r[1] or "").strip()
    offer = (r[2] or "").strip()
    if not offer and not name:
        continue
    rec = {
        "sheet_id": (r[0] or "").strip(),
        "name": name,
        "offer": offer,
        "cost_rub": to_num(r[9]) if len(r) > 9 else None,          # J
        "required_markup": to_num(r[10]) if len(r) > 10 else None,
        "wb_fee": to_num(r[11]) if len(r) > 11 else None,          # L = Комиссия+логистика ВБ
        "wb_fee_L": to_num(r[11]) if len(r) > 11 else None,        # alias: planned WB costs from col L
        "ozon_fee_plan": to_num(r[15]) if len(r) > 15 else None,   # P
        "ozon_promo_pct": to_num(r[16]) if len(r) > 16 else None,
        "ozon_final_price": to_num(r[17]) if len(r) > 17 else None,
        "wb_final_price": to_num(r[13]) if len(r) > 13 else None,
        "retail": to_num(r[23]) if len(r) > 23 else None,
        "margin_from_cost_pct": to_num(r[24]) if len(r) > 24 else None,
    }
    key = offer.upper() if offer else name.upper()
    catalog[key] = rec
    if offer:
        catalog.setdefault(offer.upper(), rec)

print("catalog rows", len(data_rows), "unique keys", len(catalog))
# samples with cost + ozon plan
with_both = [v for v in catalog.values() if v["cost_rub"] and v["ozon_fee_plan"]]
print("with cost+ozon_plan", len(with_both))
print("sample", with_both[:3])

# ---- merge with sku economics ----
econ = json.load(open(OUT / "sku_economics.json", encoding="utf-8"))

def find_cost(offer, name):
    for key in (offer.upper(), (name or "").upper()[:40]):
        if key in catalog:
            return catalog[key]
    # fuzzy: offer inside name or name startswith
    for k, v in catalog.items():
        if offer and offer.upper() in k:
            return v
        if name and v["name"] and v["name"].lower()[:18] == name.lower()[:18]:
            return v
    return None

matched = 0
for row in econ:
    g = find_cost(row.get("offer_id", ""), row.get("name", ""))
    if not g:
        row["cost_rub"] = None
        row["ozon_fee_plan"] = None
        row["sheet_name"] = None
        continue
    matched += 1
    row["cost_rub"] = g["cost_rub"]
    row["ozon_fee_plan"] = g["ozon_fee_plan"]
    row["ozon_final_price"] = g["ozon_final_price"]
    row["retail"] = g["retail"]
    row["sheet_name"] = g["name"]
    row["required_markup"] = g["required_markup"]
    qty = max(row.get("qty_sold") or 1, 1)
    payout_unit = (row.get("payout") or 0) / qty
    if g["cost_rub"]:
        row["profit_unit"] = round(payout_unit - g["cost_rub"], 2)
        row["margin_on_payout_pct"] = round((payout_unit - g["cost_rub"]) / payout_unit * 100, 1) if payout_unit else None
    # plan vs fact per unit: plan fee from sheet P vs actual total_fees/qty
    if g["ozon_fee_plan"] is not None:
        actual_fee_unit = (row.get("total_fees") or 0) / qty
        row["ozon_fee_actual_unit"] = round(actual_fee_unit, 2)
        row["ozon_fee_diff"] = round(actual_fee_unit - g["ozon_fee_plan"], 2)
        row["ozon_fee_diff_pct"] = round((actual_fee_unit - g["ozon_fee_plan"]) / g["ozon_fee_plan"] * 100, 1) if g["ozon_fee_plan"] else None

print("matched economics with sheet", matched, "/", len(econ))

# overall plan vs fact
plan_units = []
fact_units = []
diffs = []
for row in econ:
    if row.get("ozon_fee_plan") is not None and row.get("ozon_fee_actual_unit") is not None:
        plan_units.append(row["ozon_fee_plan"])
        fact_units.append(row["ozon_fee_actual_unit"])
        diffs.append(row.get("ozon_fee_diff") or 0)

plan_fact = {
    "n_matched": len(plan_units),
    "avg_plan_fee": round(sum(plan_units) / len(plan_units), 2) if plan_units else None,
    "avg_fact_fee": round(sum(fact_units) / len(fact_units), 2) if fact_units else None,
    "avg_diff": round(sum(diffs) / len(diffs), 2) if diffs else None,
    "avg_diff_pct": None,
}
if plan_fact["avg_plan_fee"] and plan_fact["avg_fact_fee"] is not None:
    plan_fact["avg_diff_pct"] = round(
        (plan_fact["avg_fact_fee"] - plan_fact["avg_plan_fee"]) / plan_fact["avg_plan_fee"] * 100, 1
    )
print("plan vs fact", plan_fact)

# cost stats
costs = [r["cost_rub"] for r in econ if r.get("cost_rub")]
print("matched costs", len(costs), "avg cost", round(sum(costs) / len(costs), 2) if costs else None)

# save
json.dump(catalog, open(OUT / "gsheet_catalog.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(econ, open(OUT / "sku_economics.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(plan_fact, open(OUT / "plan_vs_fact.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# rebuild website_data essentials
totals = json.load(open(OUT / "totals.json", encoding="utf-8"))
website = json.load(open(OUT / "website_data.json", encoding="utf-8"))
website["sku_economics"] = econ[:400]
website["plan_vs_fact_sheet"] = plan_fact
website["gsheet_catalog_sample"] = list(catalog.values())[:300]
website["gsheet_stats"] = {
    "rows": len(data_rows),
    "unique": len(catalog),
    "with_cost": sum(1 for v in catalog.values() if v["cost_rub"]),
    "with_ozon_plan": sum(1 for v in catalog.values() if v["ozon_fee_plan"] is not None),
}
json.dump(website, open(OUT / "website_data.json", "w", encoding="utf-8"), ensure_ascii=False)
print("updated website_data and sku_economics")
