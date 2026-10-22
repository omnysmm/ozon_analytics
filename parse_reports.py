"""Parse Ozon charges + realization reports into per-SKU economics."""
import openpyxl
import json
from collections import defaultdict
from datetime import datetime

CHARGES = r"C:\Users\Alex\Downloads\Отчет по начислениям_14.09.2026-14.10.2026.xlsx"
REALIZATION = r"C:\Users\Alex\Downloads\Отчет о реализации товара_20260930.xlsx"
LOGISTICS = r"C:\Users\Alex\Downloads\Отчет по логистике за период 2026-09-14 - 2026-10-14.xlsx"
OUT = r"C:\Users\Alex\ozon_analytics"


def parse_charges():
    wb = openpyxl.load_workbook(CHARGES, data_only=True, read_only=True)
    ws = wb["Начисления"]
    rows = list(ws.iter_rows(values_only=True))
    wb.close()
    header = rows[1]
    print("charges header:", header)
    print("total charge rows", len(rows) - 2)

    # columns from header
    # 0 ID, 1 date, 2 group, 3 type, 4 offer, 5 sku, 6 name, 7 qty,
    # 8 price, 9 order date, 10 platform, 11 scheme, 12 reward %,
    # 13 localization, 14 delivery time, 15 amount
    recs = []
    type_stats = defaultdict(lambda: {"n": 0, "sum": 0.0})
    for r in rows[2:]:
        if not r or not r[4]:
            continue
        rec = {
            "id": r[0],
            "date": str(r[1])[:10] if r[1] else "",
            "group": r[2] or "",
            "type": r[3] or "",
            "offer_id": r[4],
            "sku": r[5],
            "name": r[6] or "",
            "qty": r[7] or 0,
            "price": r[8] or 0,
            "order_date": str(r[9])[:10] if r[9] else "",
            "platform": r[10] or "",
            "scheme": r[11] or "",
            "reward_pct": r[12],
            "amount": float(r[15]) if r[15] is not None else 0.0,
        }
        recs.append(rec)
        t = rec["type"]
        type_stats[t]["n"] += 1
        type_stats[t]["sum"] += rec["amount"]

    print("\n=== charge types ===")
    for t, s in sorted(type_stats.items(), key=lambda x: x[1]["sum"]):
        print(f"{t:55s} n={s['n']:5d} sum={s['sum']:12.2f}")
    return recs


def parse_realization():
    wb = openpyxl.load_workbook(REALIZATION, data_only=True, read_only=True)
    ws = wb["Отчет о реализации"]
    rows = list(ws.iter_rows(values_only=True))
    wb.close()
    # find header row
    header_idx = None
    for i, r in enumerate(rows[:40]):
        vals = [str(c) if c else "" for c in r]
        joined = " ".join(vals).lower()
        if "артикул" in joined and ("сумма" in joined or "кол-во" in joined or "количество" in joined):
            header_idx = i
            print("realization header row", i, r)
            break
    if header_idx is None:
        for i, r in enumerate(rows[:30]):
            print(i, [str(c)[:30] if c else "" for c in r[:15]])
        return []
    header = rows[header_idx]
    recs = []
    for r in rows[header_idx + 1 :]:
        if not r or not r[0]:
            continue
        recs.append(list(r))
    print("realization data rows", len(recs))
    if recs:
        print("sample", recs[0])
        print("cols", len(header))
        for j, h in enumerate(header):
            print(j, h)
    return recs


def parse_logistics():
    wb = openpyxl.load_workbook(LOGISTICS, data_only=True, read_only=True)
    ws = wb["Логистика"]
    rows = list(ws.iter_rows(values_only=True))
    wb.close()
    header = rows[1]
    print("logistics header:", header)
    recs = []
    for r in rows[2:]:
        if not r or not r[3]:
            continue
        recs.append(
            {
                "type": r[2] or "",
                "offer_id": r[3],
                "sku": r[4],
                "name": r[5] or "",
                "qty": r[6] or 0,
                "price": r[7] or 0,
                "scheme": r[11] or "",
                "amount": float(r[18]) if r[18] is not None else 0.0,
            }
        )
    print("logistics rows", len(recs))
    return recs


if __name__ == "__main__":
    charges = parse_charges()
    print("\n" + "=" * 60)
    real = parse_realization()
    print("\n" + "=" * 60)
    logs = parse_logistics()

    with open(f"{OUT}\\charges_raw.json", "w", encoding="utf-8") as f:
        json.dump(charges, f, ensure_ascii=False)
    print("saved charges", len(charges))
