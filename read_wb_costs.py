import openpyxl

fp = r"C:\Users\Alex\Yandex.Disk\Pugovicnet\Цены фурнитура ВБ.xlsx"
wb = openpyxl.load_workbook(fp, data_only=True, read_only=True)
ws = wb["Лист1"]
rows = list(ws.iter_rows(values_only=True))
print("total rows", len(rows))
print("header:", rows[0])
print("--- sample ---")
for r in rows[1:25]:
    print(r)
print("--- tail ---")
for r in rows[-5:]:
    print(r)

# column count and unique names
print("cols", len(rows[0]))
# try to find offer id like columns
names = set()
for r in rows[1:]:
    if r[1]:
        names.add(str(r[1])[:60])
print("unique product names", len(names))
for n in list(names)[:30]:
    print(" -", n)
wb.close()
