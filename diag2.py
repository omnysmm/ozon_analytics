"""Validate rebuilt dashboard: structure, JS syntax, Chart.js embed."""
import re
from pathlib import Path

html = Path(r"C:\Users\Alex\ozon_analytics\index.html").read_text(encoding="utf-8")
print("size", len(html))

# leftover placeholders
print("placeholders", set(re.findall(r"__[A-Z0-9_]+__", html)))

# script integrity
print("script tags", html.count("<script"))
# </script> should close scripts; count
print("close script", html.count("</script>"))

# Chart.js embedded
print("Chart.js Chart.Element", "Chart.Element" in html or "Chart.defaults" in html)
print("has responsive", "responsive:true" in html or "responsive: true" in html)

# sections / tabs
for t in ["overview", "sku", "fees", "prices", "wb", "costs"]:
    print("sec", t, ('id="sec-' + t + '"') in html)

# handlers
for h in ["initTabs", "initFilters", "renderSkus", "renderRecs", "renderCosts", "buildCharts",
          "filterDaysByPeriod", "btnPeriod", "fSearch", "fReset", "DOMContentLoaded"]:
    print("fn", h, h in html)

# DATA keys
m = re.search(r"const DATA = (\{)", html)
print("DATA at", m.start() if m else None)

# extract main script and basic-check brackets
scripts = re.findall(r"<script>(.*?)</script>", html, re.S)
print("script blocks", len(scripts), "lens", [len(s) for s in scripts])
main = scripts[-1] if scripts else ""
# count braces in main (naive)
print("braces", main.count("{") - main.count("}"), "parens", main.count("(") - main.count(")"))
print("brackets", main.count("[") - main.count("]"))

# check JSON arrays parse
for key in ["days:", "skus:", "recs:"]:
    print(key, key in main)

# write main script for node check
Path(r"C:\Users\Alex\ozon_analytics\_main.js").write_text(main, encoding="utf-8")
print("wrote _main.js", len(main))
