from curl_cffi import requests as cr
import re
import json
from pathlib import Path

OUT = Path(r"C:\Users\Alex\ozon_analytics")

queries = [
    "Насадки для кнопок Альфа 15 мм",
    "Пресс Тер-2 для установки кнопок",
    "Насадка для кнопок Альфа 12,5",
    "Регилин китовый ус жесткий",
]

all_sellers = []
for q in queries:
    url = "https://www.ozon.ru/search/?text=" + q.replace(" ", "%20")
    try:
        r = cr.get(url, impersonate="chrome124", timeout=30)
    except Exception as e:
        print("ERR", q, e)
        continue
    print(q, r.status_code, len(r.text))
    text = r.text
    sellers = re.findall(r'"(?:sellerName|seller_name|sellerTitle|brandName|brand_title)"\s*:\s*"([^"]{2,60})"', text)
    titles = re.findall(r'"(?:title|name)"\s*:\s*"([^"]{12,100})"', text)
    prices = re.findall(r'"(?:finalPrice|price)"\s*:\s*"?(\d{2,7})"?', text)
    print("  sellers", sellers[:8])
    print("  titles", titles[:5])
    print("  prices", prices[:8])
    print("  has product cards", "/product/" in text)
    all_sellers.extend(sellers)

print("ALL unique sellers", list(dict.fromkeys(all_sellers))[:30])
(OUT / "curl_ozon_sellers.txt").write_text(
    "\n".join(dict.fromkeys(all_sellers)), encoding="utf-8"
)
