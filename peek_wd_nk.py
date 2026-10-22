import json

wd = json.load(open("website_data.json", encoding="utf-8"))
print("price_fields_note:", wd.get("price_fields_note"))
print("price_rec_formula:", wd.get("price_rec_formula"))
print("generated_at:", wd.get("generated_at"))

skus = wd.get("sku_economics") or []
print("nested sku_economics:", len(skus))
for r in skus:
    if r.get("offer_id") == "NK5415":
        print("SKU row prices:", {k: v for k, v in r.items() if "price" in k.lower() or "comp" in k.lower() or "avg" in k.lower() or k in ("offer_id", "qty")})
        break

recs = wd.get("price_recommendations") or []
print("recs:", len(recs))
for r in recs:
    if (r.get("offer_id") or r.get("offer")) == "NK5415":
        print("REC row:", r)
        break

lp = json.load(open("ozon_live_prices.json", encoding="utf-8"))
items = lp.get("items") if isinstance(lp, dict) else lp
if isinstance(lp, dict) and items is None:
    print("live keys:", list(lp.keys())[:10])
    # maybe keyed by offer
    for k, v in lp.items():
        if "NK5415" in str(k) or (isinstance(v, dict) and v.get("offer_id") == "NK5415"):
            print("live", k, v)
            break
else:
    found = 0
    for it in (items or []):
        if it.get("offer_id") == "NK5415":
            print("live item:", it)
            found += 1
    print("live items:", len(items or []), "found", found)
