"""Patient WB statistics fetcher: one call at a time, respects rate limit."""
import json
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import requests

from ozon_secrets import wb_headers

OUT = Path(r"C:\Users\Alex\ozon_analytics")
STATE = OUT / "wb_raw.json"
H = wb_headers()
END = date.today()
START = END - timedelta(days=45)
ISO = f"{START}T00:00:00.000000000"

JOBS = [
    ("sales", "GET", "https://statistics-api.wildberries.ru/api/v1/supplier/sales",
     {"dateFrom": ISO}, None),
    ("orders", "GET", "https://statistics-api.wildberries.ru/api/v1/supplier/orders",
     {"dateFrom": ISO}, None),
    ("report_detail", "GET", "https://statistics-api.wildberries.ru/api/v1/supplier/reportDetailByPeriod",
     {"dateFrom": str(START), "dateTo": str(END), "rrdId": "0"}, None),
    ("report_detail2", "GET", "https://statistics-api.wildberries.ru/api/v2/supplier/reportDetailByPeriod",
     {"dateFrom": str(START), "dateTo": str(END), "rrdId": "0"}, None),
    ("prices", "POST", "https://discounts-prices-api.wildberries.ru/api/v2/list/goods/filter",
     None, {"limit": 100, "offset": 0}),
]


def load():
    if STATE.exists():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return {"period": {"start": str(START), "end": str(END)}, "data": {}, "errors": {}}


def save(st):
    st["fetched_at"] = datetime.utcnow().isoformat() + "Z"
    STATE.write_text(json.dumps(st, ensure_ascii=False, default=str), encoding="utf-8")


def call(job, wait_cap=180):
    key, method, url, params, body = job
    st = load()
    if key in st.get("data", {}):
        print("skip", key, "already saved")
        return True
    print("CALL", key, datetime.utcnow().isoformat(), flush=True)
    try:
        if method == "GET":
            r = requests.get(url, headers=H, params=params, timeout=30)
        else:
            r = requests.post(url, headers=H, json=body, timeout=30)
    except Exception as e:
        print("EXC", key, e, flush=True)
        st.setdefault("errors", {})[key] = str(e)
        save(st)
        return False
    print(key, r.status_code, "retry", r.headers.get("X-Ratelimit-Retry"), "len", len(r.text), flush=True)
    if r.status_code == 429:
        wait = float(r.headers.get("X-Ratelimit-Retry") or 65)
        wait = min(wait, wait_cap)
        print("  sleep", wait, flush=True)
        time.sleep(wait + 1)
        return False
    if r.status_code != 200:
        st.setdefault("errors", {})[key] = {"status": r.status_code, "body": r.text[:400]}
        save(st)
        return False
    data = r.json()
    st.setdefault("data", {})[key] = data
    save(st)
    n = len(data) if isinstance(data, list) else (len(data.get("cards", data.get("data", []))) if isinstance(data, dict) else 0)
    print("  SAVED", key, "items", n, flush=True)
    return True


if __name__ == "__main__":
    deadline = time.time() + 28 * 60
    while time.time() < deadline:
        st = load()
        missing = [j for j in JOBS if j[0] not in st.get("data", {})]
        if not missing:
            print("ALL DONE", list(st["data"].keys()))
            break
        for j in list(missing):
            if time.time() > deadline:
                print("deadline reached")
                break
            ok = call(j, wait_cap=90)
            if ok:
                time.sleep(3)
            else:
                # likely rate limited — wait and retry same later
                time.sleep(2)
        # between sweeps wait at least 65s
        st = load()
        if [j for j in JOBS if j[0] not in st.get("data", {})]:
            print("sweep done, rest 65s", flush=True)
            time.sleep(65)
    st = load()
    print("final sections", list(st.get("data", {}).keys()), "errors", list(st.get("errors", {}).keys()))
