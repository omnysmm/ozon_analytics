"""Load Ozon API credentials from ozon_config.json (never commit that file)."""
import json
from pathlib import Path

_CFG = Path(__file__).resolve().parent / "ozon_config.json"


def load_ozon_config():
    if not _CFG.exists():
        raise FileNotFoundError(
            "ozon_config.json not found. Copy ozon_config.example.json and fill in keys."
        )
    cfg = json.loads(_CFG.read_text(encoding="utf-8"))
    return {
        "client_id": str(cfg["ozon_client_id"]),
        "key": cfg.get("ozon_api_key_analytics") or cfg.get("ozon_api_key_content"),
        "key_content": cfg.get("ozon_api_key_content"),
        "key_analytics": cfg.get("ozon_api_key_analytics"),
        "gsheet_url": cfg.get("gsheet_url"),
        "wb_token": cfg.get("wb_api_token"),
    }


def wb_headers():
    cfg = load_ozon_config()
    if not cfg.get("wb_token"):
        raise FileNotFoundError("wb_api_token missing in ozon_config.json")
    return {"Authorization": cfg["wb_token"], "Content-Type": "application/json"}


def ozon_headers(key=None):
    cfg = load_ozon_config()
    return {
        "Api-Key": key or cfg["key"],
        "Client-Id": cfg["client_id"],
        "Content-Type": "application/json",
    }
