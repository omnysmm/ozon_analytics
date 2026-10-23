"""Quick WB fetch with short timeouts; save each section immediately."""
import json
import time
from datetime import date, datetime, timedelta
from pathlib import Path
import requests

from ozon_secrets import wb_headers

OUT = Path(r"C:\Users\Alex\ozon_analytics")
H = wb_headers()
END = date.today()
START = END - timedelta(days=45)
ISO = f"{START}T00:00:00.000000000"
STATE = OUT / "wb_raw.json"


def load_state():
    if STATE.exists():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return {"fetched_at": None, "period": {"start": str(START), "end": str(END)}, "data": {}}


def save_state(st):
    st["fetched_at"] = datetime.utcnow().isoformat() + "Z"
    STATE.write_text(json.dumps(st, ensure_ascii=False, default=str), encoding="utf-8")


def get(url, params=None, key=None, tries=4):
    st = load_state()
    for i in range(tries):
        try:
            r = requests.get(url, headers=H, params=params, timeout=25)
        except Exception as e:
            print(key or url, "EXC", e)
            time.sleep(2)
            continue
        print((key or url), r.status_code, "len", len(r.text), "hdr", r.headers.get("X-RateLimit-Retry"))
        if r.status_code == 429:
            wait = float(r.headers.get("X-RateLimit-Retry") or (3 * (i + 1)))
            time.sleep(wait + 0.5)
            continue
        if r.status_code == 200:
            data = r.json()
            st["data"][key or url] = data
            save_state(st)
            if isinstance(data, list):
                print("  ->", len(data), "items")
            else:
                print("  ->", list(data)[:15] if isinstance(data, dict) else type(data))
            return data
        print("  body", r.text[:200])
        st["data"].setdefault("_errors", {})[key or url] = {"status": r.status_code, "body": r.text[:300]}
        save_state(st)
        return None
    return None


def post(url, body, key, tries=3):
    st = load_state()
    for i in range(tries):
        try:
            r = requests.post(url, headers=H, json=body, timeout=25)
        except Exception as e:
            print(key, "EXC", e)
            time.sleep(2)
            continue
        print(key, r.status_code, "len", len(r.text), "hdr", r.headers.get("X-RateLimit-Retry"))
        if r.status_code == 429:
            time.sleep(float(r.headers.get("X-RateLimit-Retry") or 3) + 0.5)
            continue
        if r.status_code == 200:
            data = r.json()
            st["data"][key] = data
            save_state(st)
            print("  -> keys", list(data)[:15] if isinstance(data, dict) else (len(data) if isinstance(data, list) else type(data)))
            return data
        print("  body", r.text[:200])
        st["data"].setdefault("_errors", {})[key] = {"status": r.status_code, "body": r.text[:300]}
        save_state(st)
        return None
    return None


if __name__ == "__main__":
    get("https://statistics-api.wildberries.ru/api/v1/supplier/sales", {"dateFrom": ISO}, "sales")
    get("https://statistics-api.wildberries.ru/api/v1/supplier/orders", {"dateFrom": ISO}, "orders")
    get("https://statistics-api.wildberries.ru/api/v1/supplier/reportDetailByPeriod",
        {"dateFrom": str(START), "dateTo": str(END), "rrdId": "0"}, "report_detail")
    post("https://content-api.wildberries.ru/content/v2/get/cards/list",
         {"cursor": {"limit": 50}}, "cards")
    print("DONE sections", list(load_state()["data"].keys()))
