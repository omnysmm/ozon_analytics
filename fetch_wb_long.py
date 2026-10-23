"""Long-running WB statistics fetch: waits full X-Ratelimit-Retry, saves when ready."""
import json
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

from ozon_secrets import wb_headers

OUT = Path(r"C:\Users\Alex\ozon_analytics")
STATE = OUT / "wb_raw.json"
LOG = OUT / "wb_fetch.log"
H = wb_headers()
END = date.today()
START = END - timedelta(days=60)
ISO = f"{START}T00:00:00.000000000"

JOBS = [
    ("sales", "GET", "https://statistics-api.wildberries.ru/api/v1/supplier/sales", {"dateFrom": ISO}, None),
    ("orders", "GET", "https://statistics-api.wildberries.ru/api/v1/supplier/orders", {"dateFrom": ISO}, None),
]


def log(msg):
    line = datetime.now(timezone.utc).strftime("%H:%M:%S ") + msg
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def load():
    if STATE.exists():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return {"period": {"start": str(START), "end": str(END)}, "data": {}, "errors": {}}


def save(st):
    st["fetched_at"] = datetime.now(timezone.utc).isoformat()
    STATE.write_text(json.dumps(st, ensure_ascii=False, default=str), encoding="utf-8")


def fetch_once(key, method, url, params, body):
    st = load()
    if key in st.get("data", {}):
        log("have " + key)
        return "have"
    try:
        if method == "GET":
            r = requests.get(url, headers=H, params=params, timeout=30)
        else:
            r = requests.post(url, headers=H, json=body or {}, timeout=30)
    except Exception as e:
        log("EXC " + key + " " + str(e)[:120])
        return "err"
    retry = r.headers.get("X-Ratelimit-Retry") or r.headers.get("X-RateLimit-Retry")
    log(f"{key} {r.status_code} retry={retry} len={len(r.text)}")
    if r.status_code == 429:
        wait = float(retry or 60)
        return "limit:" + str(wait)
    if r.status_code != 200:
        st.setdefault("errors", {})[key] = {"status": r.status_code, "body": r.text[:300]}
        save(st)
        return "fail"
    data = r.json()
    st.setdefault("data", {})[key] = data
    save(st)
    n = len(data) if isinstance(data, list) else 0
    log("SAVED " + key + " n=" + str(n))
    return "ok"


if __name__ == "__main__":
    log("START long fetcher")
    while True:
        st = load()
        missing = [j for j in JOBS if j[0] not in st.get("data", {})]
        if not missing:
            log("ALL DONE " + str(list(st["data"].keys())))
            break
        for job in missing:
            status = fetch_once(*job)
            if status.startswith("limit:"):
                wait = float(status.split(":", 1)[1])
                wait = min(wait + 2, 3600)
                log("wait " + str(int(wait)) + "s for " + job[0])
                time.sleep(wait)
            elif status == "ok":
                time.sleep(5)
            elif status == "fail":
                time.sleep(30)
            else:
                time.sleep(10)
        time.sleep(20)
    log("EXIT")
