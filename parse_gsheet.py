"""Parse Google Sheet: column J = cost, column P = planned Ozon costs."""
import csv
import json
from pathlib import Path

OUT = Path(r"C:\Users\Alex\ozon_analytics")
raw = (OUT / "gsheet_download.bin").read_bytes()
text = raw.decode("utf-8-sig", errors="replace")
# save clean csv
(OUT / "gsheet.csv").write_text(text, encoding="utf-8")

rows = list(csv.reader(text.splitlines()))
print("rows", len(rows), "cols", len(rows[0]) if rows else 0)

# header row is row 0 (after first data cell? first cell was offer id)
# From sample: first row starts with offer id then headers...
# Actually looking at sample: 'KNP11-KAM-MWHITE30,Артикул,,Вес...'
# That looks like row 0 is DATA with weird headers? Or headers start from col B?
# Let's print first 3 rows with indices

for i, r in enumerate(rows[:3]):
    print(f"\n=== ROW {i} ncols={len(r)} ===")
    for j, c in enumerate(r):
        letter = chr(ord('A') + j) if j < 26 else 'A' + chr(ord('A') + j - 26)
        print(f"  {letter} [{j}] = {c[:60]!r}")
