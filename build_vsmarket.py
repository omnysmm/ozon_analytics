"""Build 'we vs market' per-SKU dataset v2: trust Ozon price_index_value/color, October sales, recommendations."""
import json
from pathlib import Path

OUT = Path(r"C:\Users\Alex\ozon_analytics")

oct_rows = json.load(open(OUT / "oct_sales_by_sku.json", encoding="utf-8"))
prices = json.load(open(OUT / "price_indexes_fresh.json", encoding="utf-8"))
econ = json.load(open(OUT / "sku_economics.json", encoding="utf-8"))
try:
    plist = json.load(open(OUT / "ozon_products_list.json", encoding="utf-8"))
except Exception:
    plist = []

sku2offer = {}
if plist and isinstance(plist, list):
    for p in plist:
        if isinstance(p, dict) and p.get("sku") and p.get("offer_id"):
            sku2offer[str(p["sku"])] = p["offer_id"]
for e in econ:
    if e.get("sku") and e.get("offer_id"):
        sku2offer[str(e["sku"])] = e["offer_id"]

econ_by_offer = {e["offer_id"]: e for e in econ if e.get("offer_id")}
price_by_offer = {p["offer_id"]: p for p in prices if p.get("offer_id")}
oct_by_offer = {}
for r in oct_rows:
    off = sku2offer.get(str(r.get("sku")))
    if off:
        oct_by_offer[off] = r

# competitor links resolved from storefront search (partial: top SKUs)
comp_by_offer = {}
try:
    comp_raw = json.load(open(OUT / "competitor_links.json", encoding="utf-8"))
    for off, v in comp_raw.items():
        c = (v or {}).get("comp")
        if c and c.get("href"):
            href = c["href"]
            if href.startswith("/"):
                href = "https://www.ozon.ru" + href
            href = href.split("?")[0]
            comp_by_offer[off] = {"comp_price": c.get("price"), "comp_href": href, "comp_name": c.get("name")}
except Exception:
    pass
print("competitor links loaded:", len(comp_by_offer))

rows = []
all_offers = sorted(set(list(price_by_offer) + list(econ_by_offer) + list(oct_by_offer)))
for off in all_offers:
    p = price_by_offer.get(off, {})
    e = econ_by_offer.get(off, {})
    o = oct_by_offer.get(off, {})

    price_blk = p.get("price") or {}
    our_price = price_blk.get("price") or e.get("seller_price_api") or e.get("price_ozon") or e.get("min_price")
    old_price = price_blk.get("old_price") or e.get("old_price")

    idx = p.get("price_indexes") or {}
    ext = idx.get("external_index_data") or {}
    oz = idx.get("ozon_index_data") or {}
    sm = idx.get("self_marketplaces_index_data") or {}

    def minp(d):
        v = d.get("min_price") or 0
        return v if v > 0 else None

    m_ext, m_oz, m_sm = minp(ext), minp(oz), minp(sm)
    markets = [m for m in (m_ext, m_oz, m_sm) if m]
    min_market = min(markets) if markets else None

    color = idx.get("color_index") or e.get("price_index_color") or "WITHOUT_INDEX"
    # prefer ozon index (other Ozon sellers), then external, then self; keep color from same source
    val, val_src, val_color = 0, None, None
    for src, d in (("ozon", oz), ("external", ext), ("self", sm)):
        v = d.get("price_index_value") or 0
        if v > 0:
            val, val_src = v, src
            val_color = d.get("price_index_color")
            break
    if not val and e.get("price_index_value"):
        val = e.get("price_index_value")
        val_src = "econ"
        val_color = e.get("price_index_color")
    if val and val_color:
        color = val_color

    dev_pct = round((val - 1) * 100, 1) if val else None  # + = дороже рынка, - = дешевле

    oct_qty = int(o.get("ordered_units") or 0)
    oct_rev = float(o.get("revenue") or 0)
    oct_ret = int(o.get("returns") or 0)
    oct_views = int(o.get("session_view") or 0)
    conv = round(oct_qty / oct_views * 100, 2) if oct_views else None
    ret_rate = round(oct_ret / oct_qty * 100, 1) if oct_qty else None

    profit = e.get("profit_unit")
    margin = e.get("margin_on_payout_pct")
    cost = e.get("cost_rub")

    flags = []
    if color == "RED":
        flags.append(f"Цена выше рынка ({'+' if (dev_pct or 0) >= 0 else ''}{dev_pct}% по индексу)")
    elif color == "YELLOW":
        flags.append(f"Цена слегка выше рынка ({'+' if (dev_pct or 0) >= 0 else ''}{dev_pct}%)")
    elif color == "WITHOUT_INDEX" or val == 0:
        flags.append("Нет данных рынка (без индекса)")
    if color == "SUPER" and margin is not None and margin < 25:
        flags.append(f"Цена ниже рынка при марже {margin}%")
    if oct_qty == 0 and oct_views > 0:
        flags.append("Нет продаж при трафике")
    if oct_views == 0:
        flags.append("Нет трафика")
    if conv is not None and conv < 1 and oct_views > 50:
        flags.append(f"Низкая конверсия ({conv}%)")
    if ret_rate is not None and ret_rate >= 15:
        flags.append(f"Высокие возвраты ({ret_rate}%)")
    if profit is not None and profit <= 0:
        flags.append("Убыточная экономика")
    elif margin is not None and margin < 15:
        flags.append(f"Низкая маржа ({margin}%)")

    recs = []
    if color == "RED":
        target = f" (минимум рынка по данным Ozon: {min_market} ₽)" if min_market else ""
        if oct_qty > 0:
            recs.append(f"Снизить цену к уровню рынка: индекс {val}, отклонение +{dev_pct}%{target} — либо усилить УТП/карточку")
        else:
            recs.append(f"Цена выше рынка (+{dev_pct}%) при нулевых продажах — снизить до уровня рынка{target} или пересобрать карточку")
    elif color == "YELLOW":
        recs.append(f"Цена слегка выше рынка ({'+' if (dev_pct or 0) >= 0 else ''}{dev_pct}%) — точечное снижение или бонус (доставка/подарок)")
    elif color == "SUPER":
        if margin is not None and margin < 25:
            recs.append(f"Индекс {val} (дешевле рынка) при марже {margin}% — есть запас для повышения цены")
        else:
            recs.append(f"Индекс {val} — цена заметно ниже рынка: протестировать повышение")
    elif color == "WITHOUT_INDEX" or val == 0:
        recs.append("Нет индекса рынка — контролировать цены конкурентов вручную (поиск Ozon)")

    if oct_views == 0:
        recs.append("Трафика нет: добавить в продвижение, расширить ключевые слова в карточке")
    elif conv is not None and conv < 1 and oct_views > 50:
        recs.append(f"Поднять конверсию (сейчас {conv}%): фото/видео, инфографика, отзывы, вопросы-ответы")
    if ret_rate is not None and ret_rate >= 15:
        recs.append(f"Снизить возвраты ({ret_rate}%): сверить описание/размеры, упаковку, качество")
    if profit is not None and profit <= 0:
        recs.append("Экономика убыточна: поднять цену или снизить себестоимость/расходы")
    elif margin is not None and margin < 15:
        recs.append(f"Маржа {margin}% — оптимизировать затраты или цену")
    if not recs:
        recs.append("Позиция конкурентоспособна — удерживать цену")

    comp = comp_by_offer.get(off) or {}
    rows.append({
        "offer_id": off,
        "name": e.get("name") or o.get("name") or "",
        "sku": e.get("sku"),
        "our_price": our_price,
        "old_price": old_price,
        "min_market": min_market,
        "min_external": m_ext,
        "min_ozon": m_oz,
        "min_self": m_sm,
        "comp_price": comp.get("comp_price"),
        "comp_href": comp.get("comp_href"),
        "comp_name": comp.get("comp_name"),
        "index_value": val or None,
        "index_src": val_src,
        "dev_pct": dev_pct,
        "index_color": color,
        "oct_qty": oct_qty,
        "oct_rev": round(oct_rev),
        "oct_returns": oct_ret,
        "oct_views": oct_views,
        "conv_pct": conv,
        "return_rate": ret_rate,
        "cost_rub": cost,
        "profit_unit": profit,
        "margin_pct": margin,
        "flags": flags,
        "flag_str": "; ".join(flags),
        "recommendation": " | ".join(recs),
    })

rows.sort(key=lambda r: -r["oct_rev"])

red = [r for r in rows if r["index_color"] == "RED"]
yel = [r for r in rows if r["index_color"] == "YELLOW"]
sup = [r for r in rows if r["index_color"] == "SUPER"]
grn = [r for r in rows if r["index_color"] == "GREEN"]
noi = [r for r in rows if r["index_color"] in ("WITHOUT_INDEX", None) or not r["index_value"]]
devs = [r["dev_pct"] for r in rows if r["dev_pct"] is not None and r["index_color"] != "WITHOUT_INDEX"]
kpi = {
    "n_rows": len(rows),
    "n_red": len(red), "n_yellow": len(yel), "n_super": len(sup),
    "n_green": len(grn), "n_noindex": len(noi),
    "avg_dev_pct": round(sum(devs) / len(devs), 1) if devs else 0,
    "oct_rev_total": round(sum(r["oct_rev"] for r in rows)),
    "oct_qty_total": sum(r["oct_qty"] for r in rows),
    "rev_at_risk": round(sum(r["oct_rev"] for r in red + yel)),
    "n_dead": sum(1 for r in rows if r["oct_qty"] == 0),
    "n_no_traffic": sum(1 for r in rows if r["oct_views"] == 0),
    "n_high_returns": sum(1 for r in rows if (r["return_rate"] or 0) >= 15),
    "n_low_conv": sum(1 for r in rows if r["conv_pct"] is not None and r["conv_pct"] < 1 and r["oct_views"] > 50),
    "n_loss": sum(1 for r in rows if r["profit_unit"] is not None and r["profit_unit"] <= 0),
    "period": "2026-10-01 — 2026-10-31",
    "built_at": "2026-11-09",
}

json.dump({"kpi": kpi, "rows": rows}, open(OUT / "vsmarket.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(kpi, ensure_ascii=False, indent=1))
print("\nTop-10 by Oct revenue:")
for r in rows[:10]:
    print(f"  {r['offer_id'][:16]:16s} idx={str(r['index_value']):5s} {str(r['index_color']):13s} dev={str(r['dev_pct']):6s} "
          f"qty={r['oct_qty']:4d} rev={r['oct_rev']:8d} | {r['flag_str'][:56]}")
print("\nwrote vsmarket.json")
