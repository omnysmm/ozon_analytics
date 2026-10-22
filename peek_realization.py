"""Full realization report parse + unified SKU economics."""
import openpyxl
import json
from collections import defaultdict

REALIZATION = r"C:\Users\Alex\Downloads\Отчет о реализации товара_20260930.xlsx"
OUT = r"C:\Users\Alex\ozon_analytics"

wb = openpyxl.load_workbook(REALIZATION, data_only=True, read_only=True)
ws = wb["Отчет о реализации"]
rows = list(ws.iter_rows(values_only=True))
wb.close()

# print rows 12-16 with ALL columns
for i in range(12, 18):
    r = rows[i]
    print(f"ROW {i} ncols={len(r)}")
    for j, c in enumerate(r):
        if c is not None:
            print(f"  [{j}] {c}")
    print()

# find max col with data in header area
print("row13 full:")
for j, c in enumerate(rows[13]):
    print(f"  [{j}] {c}")
print("row12 full:")
for j, c in enumerate(rows[12]):
    print(f"  [{j}] {c}")
