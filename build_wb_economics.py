"""Build WB economics JSON from cards + sales/orders (read-only). Merge costs from Google Sheet J."""
import json
from collections import defaultdict
from pathlib import Path

OUT = Path(r"C:\Users\Alex\ozon_analytics")

# --- cards ---
cards_raw = json.load(open(OUT / "wb_cards.json", encoding="utf-8"))
cards = {}
for c in cards_raw:
    cards[c["nmID"]] = c
print("WB cards unique", len(cards))

# --- optional raw stats ---
raw = {}
if (OUT / "wb_raw.json").exists():
    raw = json.load(open(OUT / "wb_raw.json", encoding="utf-8"))
data = raw.get("data") or {}
sales = data.get("sales") or []
orders = data.get("orders") or []
report = data.get("report_detail") or data.get("report_detail2") or []
print("sales", len(sales), "orders", len(orders), "report", len(report) if isinstance(report, list) else type(report))

# --- gsheet costs (col J / P / K) ---
sheet_cost = {}
try:
    import csv
    with open(OUT / "gsheet.csv", encoding="utf-8") as f:
        # try to find cost columns from existing parse helpers
        pass
except Exception:
    pass

# reuse gsheet_catalog.json if present (dict: offer -> {cost_rub, wb_fee, wb_final_price, ...})
gs = {}
gpath = OUT / "gsheet_catalog.json"
if gpath.exists():
    raw_gs = json.load(open(gpath, encoding="utf-8"))
    if isinstance(raw_gs, dict):
        for k, v in raw_gs.items():
            if isinstance(v, dict):
                gs[str(k).strip().upper()] = v
            elif isinstance(v, dict) or True:
                pass
    elif isinstance(raw_gs, list):
        for it in raw_gs:
            if not isinstance(it, dict):
                continue
            key = (it.get("offer_id") or it.get("offer") or it.get("sku") or "").strip()
            if key:
                gs[key.upper()] = it
print("gsheet rows", len(gs))

# map vendorCode -> gsheet cost fields
def find_cost(vendor):
    if not vendor:
        return {}
    v = str(vendor).strip().upper()
    for key in (v, v.replace("-", ""), v.replace("_", "-"), v.replace(" ", "")):
        if key in gs:
            return gs[key]
    # fuzzy prefix
    alnum = "".join(ch for ch in v if ch.isalnum())
    for k, it in gs.items():
        ka = "".join(ch for ch in k if ch.isalnum())
        if alnum and ka and (alnum.startswith(ka[:10]) or ka.startswith(alnum[:10])):
            return it
    return {}


def num(x, default=None):
    if x is None or x == "":
        return default
    try:
        return float(x)
    except Exception:
        return default


# --- aggregate sales by nmID ---
agg = defaultdict(lambda: {
    "qty": 0, "revenue": 0.0, "discounts": 0.0, "for_pay": 0.0, "returns": 0,
    "order_qty": 0, "price_avg_sum": 0.0, "price_avg_n": 0,
    "skus": set(), "sale_types": [],
})

for s in sales if isinstance(sales, list) else []:
    nm = s.get("nmId") or s.get("nmID") or s.get("nmid")
    if not nm:
        continue
    a = agg[nm]
    a["qty"] += 1
    a["skus"].add(s.get("sku") or s.get("barcode") or "")
    price = num(s.get("totalPrice")) or 0
    sale_price = num(s.get("salePrice") or s.get("priceWithDisc")) or 0
    a["revenue"] += sale_price
    a["discounts"] += (price - sale_price) if price else 0
    if s.get("forPay") is not None:
        a["for_pay"] += num(s.get("forPay")) or 0
    if str(s.get("saleID") or "").startswith("R"):
        a["returns"] += 1
    if sale_price:
        a["price_avg_sum"] += sale_price
        a["price_avg_n"] += 1
    a["sale_types"].append(s.get("saleID"))

for o in orders if isinstance(orders, list) else []:
    nm = o.get("nmId") or o.get("nmID") or o.get("nmid")
    if not nm:
        continue
    agg[nm]["order_qty"] += 1

# --- report by nm (if any) ---
rep_by_nm = defaultdict(lambda: {"fees": 0.0, "payout": 0.0, "qty": 0, "revenue": 0.0, "supp": 0.0, "logistics": 0.0})
if isinstance(report, list):
    for r in report:
        nm = r.get("nmId") or r.get("nmID") or r.get("nmid")
        if not nm:
            continue
        e = rep_by_nm[nm]
        for field, key in [
            ("quantity", "qty"), ("retail_price_withdisc", "revenue"),
            ("supplier_reward", "fees"), ("for_pay", "payout"),
            ("rebill_logistic_cost", "logistics"), ("acceptance", "supp"),
        ]:
            v = num(r.get(field))
            if v is not None:
                e[key] += v

rows = []
for nm, c in cards.items():
    vendor = c.get("vendorCode") or ""
    a = agg.get(nm) or {}
    g = find_cost(vendor)
    qty = a.get("qty") or 0
    revenue = round(a.get("revenue") or 0, 2)
    avg_price = round((a.get("price_avg_sum") or 0) / a["price_avg_n"], 2) if a.get("price_avg_n") else None
    for_pay = round(a.get("for_pay") or 0, 2)
    # fallback payout model if no forPay
    take_pct_model = 20.0
    if for_pay <= 0 and revenue > 0:
        for_pay = round(revenue * (1 - take_pct_model / 100), 2)
    payout_unit = round(for_pay / qty, 2) if qty else None

    cost_rub = num(g.get("cost_rub"))  # Google Sheet column J
    # WB planned costs MUST come from Google Sheet column L («Комиссия+логистика ВБ»)
    wb_fee_plan = num(g.get("wb_fee") or g.get("wb_fee_L") or g.get("L"))
    wb_final_price = num(g.get("wb_final_price"))  # column N
    required_markup = num(g.get("required_markup"))  # column K
    sheet_name = g.get("name") or None

    profit_unit = None
    margin_pct = None
    if payout_unit is not None and cost_rub is not None:
        profit_unit = round(payout_unit - cost_rub, 2)
        margin_pct = round(profit_unit / payout_unit * 100, 1) if payout_unit else None

    # if no sales yet, derive plan economics from sheet wb_final_price
    if profit_unit is None and wb_final_price and cost_rub is not None and wb_fee_plan is not None:
        plan_payout = wb_final_price - wb_fee_plan
        profit_unit = round(plan_payout - cost_rub, 2)
        margin_pct = round(profit_unit / plan_payout * 100, 1) if plan_payout else None
        payout_unit = round(plan_payout, 2)
        if not revenue and wb_final_price:
            avg_price = wb_final_price

    # plan revenue if zero sales (1 unit plan) for comparison totals
    plan_revenue = wb_final_price if wb_final_price is not None else None
    plan_payout_total = None
    if plan_revenue is not None and wb_fee_plan is not None:
        plan_payout_total = round(plan_revenue - wb_fee_plan, 2)

    row = {
        "nmId": nm,
        "offer_id": vendor or str(nm),
        "name": sheet_name or c.get("title") or vendor or f"WB {nm}",
        "subject": c.get("subjectName"),
        "barcode": (c.get("sizes") or [{}])[0].get("skus", [None])[0] if c.get("sizes") else None,
        "qty_sold": qty,
        "qty_ordered": a.get("order_qty") or 0,
        "qty_returns": a.get("returns") or 0,
        "wb_revenue": revenue,
        "wb_avg_price": avg_price,
        "wb_payout": for_pay,
        "wb_payout_unit": payout_unit,
        "wb_take_pct": round((revenue - for_pay) / revenue * 100, 2) if revenue and for_pay else take_pct_model,
        "cost_rub": cost_rub,
        "wb_fee_plan": wb_fee_plan,
        "wb_fee_source": "gsheet_col_L",
        "wb_final_price": wb_final_price,
        "wb_plan_revenue_unit": plan_revenue,
        "wb_plan_payout_unit": plan_payout_total,
        "required_markup": required_markup,
        "profit_unit": profit_unit,
        "margin_on_payout_pct": margin_pct,
        "cost_source": "gsheet" if cost_rub is not None else None,
        "sales_source": "wb_api" if qty else ("plan_gsheet" if plan_revenue is not None else "wb_api_empty"),
        "report_source": "wb_api" if any(rep_by_nm.get(nm, {}).values()) else "model",
    }
    # report enrich
    e = rep_by_nm.get(nm)
    if e and e.get("qty"):
        row["wb_qty_report"] = e["qty"]
        row["wb_revenue_report"] = round(e["revenue"], 2)
        row["wb_fees_report"] = round(e["fees"], 2)
        row["wb_payout_report"] = round(e["payout"], 2)
    rows.append(row)

rows.sort(key=lambda r: -(r.get("wb_revenue") or 0))

totals = {
    "qty_sold": sum(r.get("qty_sold") or 0 for r in rows),
    "qty_ordered": sum(r.get("qty_ordered") or 0 for r in rows),
    "wb_revenue": round(sum(r.get("wb_revenue") or 0 for r in rows), 2),
    "wb_payout": round(sum(r.get("wb_payout") or 0 for r in rows), 2),
    "n_cards": len(rows),
    "n_with_sales": sum(1 for r in rows if r.get("qty_sold")),
    "n_with_cost": sum(1 for r in rows if r.get("cost_rub") is not None),
}
if totals["wb_revenue"]:
    totals["wb_take_pct"] = round((totals["wb_revenue"] - totals["wb_payout"]) / totals["wb_revenue"] * 100, 2)
else:
    totals["wb_take_pct"] = take_pct_model

# plan comparison units when sales empty
totals["wb_plan_revenue_sum"] = round(sum(r.get("wb_plan_revenue_unit") or 0 for r in rows), 2)
totals["wb_plan_payout_sum"] = round(sum(r.get("wb_plan_payout_unit") or 0 for r in rows), 2)
if totals["wb_plan_revenue_sum"]:
    totals["wb_plan_take_pct"] = round(
        (totals["wb_plan_revenue_sum"] - totals["wb_plan_payout_sum"]) / totals["wb_plan_revenue_sum"] * 100, 2
    )
totals["data_mode"] = "sales" if totals["qty_sold"] else "plan"

payload = {
    "generated_at": raw.get("fetched_at") or "cards_only",
    "period": raw.get("period") or {"start": "n/a", "end": "n/a"},
    "totals": totals,
    "skus": rows,
    "notes": {
        "read_only": True,
        "token_stats_limit": "statistics-api rate limit 1 req/window",
        "report_detail": "404 on current account paths — fees modeled until report API available",
    },
}
outp = OUT / "wb_economics.json"
json.dump(payload, open(outp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("wrote", outp)
print("totals", totals)
for r in rows[:8]:
    print(r["offer_id"], "qty", r["qty_sold"], "rev", r["wb_revenue"], "pay/u", r["wb_payout_unit"],
          "cost", r["cost_rub"], "profit", r["profit_unit"], "take%", r["wb_take_pct"])
