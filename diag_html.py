import re
html = open(r"C:\Users\Alex\ozon_analytics\index.html", encoding="utf-8").read()
print("len", len(html))
print("chart.js", "chart.umd" in html)
print("canvas", html.count("<canvas"))
print("script tags", html.count("<script"))
print("const DATA", "const DATA" in html)
idx = html.find("const DATA")
print("DATA at", idx)
print(html[idx : idx + 300])
print("--- placeholders ---")
print(set(re.findall(r"__[A-Z0-9_]+__", html)))
print("--- sections ---")
for t in ["overview", "sku", "fees", "prices", "wb", "costs"]:
    print("sec-" + t, ('id="sec-' + t + '"') in html)
# JSON parse of skus
m = re.search(r"skus:\s*(\[.*?\])\s*,\s*\n\s*recs:", html, re.S)
print("skus json", bool(m))
if m:
    import json

    try:
        arr = json.loads(m.group(1))
        print("skus len", len(arr), "keys", list(arr[0].keys())[:12] if arr else None)
    except Exception as e:
        print("skus json err", e)
# check for </script> inside JSON strings
body = html[idx:]
end = html.find("</script>", idx)
chunk = html[idx:end]
print("chunk len", len(chunk), "has raw </script> in data?", "</script>" in chunk[:-10])
# look for NaN/Infinity
print("NaN", "NaN" in html, "Infinity", "Infinity" in html)
# tab handler
print("tabs handler", "data-tab" in html)
print("renderSkus", "renderSkus" in html)
