import os
import sqlite3
import sys
from datetime import datetime
from typing import Any, Dict, List

import requests

# ---------------------- НАЛАШТУВАННЯ ----------------------
DB_PATH = os.path.join(".data", "fx_rates.sqlite3")

OBS_LATEST_BYGROUP_URL = "https://api.riksbank.se/swea/v1/Observations/Latest/ByGroup/130"
TIMEOUT = 20


# ---------------------- УТИЛІТИ ---------------------------
def log(msg: str) -> None:
    ts = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    print(f"[{ts}] {msg}", flush=True)


def ensure_db() -> None:
    os.makedirs(".data", exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        with open(os.path.join("sql", "001_init.sql"), "r", encoding="utf-8") as f:
            conn.executescript(f.read())


def http_get(url: str) -> Any:
    r = requests.get(url, timeout=TIMEOUT, headers={"accept": "application/json"})
    r.raise_for_status()
    return r.json()


# ---------------------- API CALL --------------------------
def fetch_latest_by_group() -> List[Dict[str, Any]]:
    """
    Єдиний потрібний запит:
    GET /Observations/Latest/ByGroup/130
    Формат відповіді:
    [{"seriesId":"SEKUSDPMI","date":"2025-09-05","value":9.40498}, ...]
    """
    log("Fetching latest FX rates for group 130...")
    data = http_get(OBS_LATEST_BYGROUP_URL)

    if not isinstance(data, list):
        log("Unexpected API format (expected list).")
        return []

    rows: List[Dict[str, Any]] = []
    for item in data:
        try:
            sid = item.get("seriesId")
            date = item.get("date")
            value = float(item.get("value"))
            if sid and date and value is not None:
                rows.append({"series_id": sid, "obs_date": date, "value": value})
        except Exception:
            continue

    log(f"Fetched {len(rows)} observations.")
    return rows


# ---------------------- БД ОПЕРАЦІЇ ----------------------
def upsert_observation(conn: sqlite3.Connection, obs: Dict[str, Any]) -> None:
    now = datetime.utcnow().isoformat()
    conn.execute(
        """
        INSERT INTO observations (series_id, obs_date, value, received_at)
        VALUES (:series_id, :obs_date, :value, :now)
        ON CONFLICT(series_id, obs_date) DO UPDATE SET
            value=excluded.value
        """,
        {**obs, "now": now},
    )


# ---------------------- MAIN ------------------------------
def main() -> int:
    ensure_db()

    latest_list = fetch_latest_by_group()
    if not latest_list:
        log("No data returned.")
        return 0

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA foreign_keys=ON;")
        for obs in latest_list:
            try:
                conn.execute("BEGIN;")
                upsert_observation(conn, obs)
                conn.commit()
                log(f"Saved {obs['series_id']}: {obs['obs_date']} = {obs['value']}")
            except Exception as e:
                log(f"Failed {obs.get('series_id','?')}: {e}")

    log("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

