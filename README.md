````markdown
# get-rates-app
A tiny Python app that fetches the latest FX rates from the Riksbank SWEA API.
According to the API documentation, all the latest FX rate data are available in a single request,
so the app is designed in the simplest and most straightforward way.
The retrieved rates are stored in a local SQLite database.

````
---

## Contents

* [Requirements](#requirements)
* [How It Works](#how-it-works)
* [Database & Queries](#database--queries)
* [Scheduling (cron / systemd / Task Scheduler)](#scheduling-cron--systemd--task-scheduler)
* [Formatting (black)](#formatting-black)
* [Notes](#notes)

---

## Requirements

* **Python 3.10.8** (exact version)
* **Poetry** (dependency management & isolated virtualenv)
* Internet access to reach `api.riksbank.se`

> SQLite is part of Python’s standard library (`sqlite3`), no extra DB server required.

---

## How It Works

* The app calls **`/Observations/Latest/ByGroup/130`** once and receives a list of records:
  - API endpoint (single call):  
  `GET https://api.riksbank.se/swea/v1/Observations/Latest/ByGroup/130`
  - Response format example:
  ```json
  {"seriesId":"SEKUSDPMI","date":"YYYY-MM-DD","value":9.40498}
  ```
* Each record is stored as one row in `observations`.
* `PRIMARY KEY (series_id, obs_date)` keeps historical data unique and allows idempotent reruns.
* A `received_at` timestamp records when the row was stored.

---

## Database & Queries

* DB file: **`.data/fx_rates.sqlite3`** (excluded from git by `.gitignore`).

### Inspect data quickly

```bash
sqlite3 -header -column .data/fx_rates.sqlite3 \
"SELECT series_id, obs_date, value FROM observations ORDER BY obs_date DESC, series_id LIMIT 10;"
```

### Examples

* Latest date values:

```sql
SELECT series_id, obs_date, value
FROM observations
WHERE obs_date = (SELECT MAX(obs_date) FROM observations)
ORDER BY series_id;
```

* Specific series (e.g., SEK→USD):

```sql
SELECT obs_date, value
FROM observations
WHERE series_id = 'SEKUSDPMI'
ORDER BY obs_date DESC
LIMIT 20;
```

---

## Scheduling (cron / systemd / Task Scheduler)

Run **once a day** to keep history updated.

### macOS / Linux: cron

```bash
crontab -e
# Every day at 08:00 (local time)
0 8 * * * cd /absolute/path/to/repo && /usr/local/bin/poetry run get-rates-app >> .data/cron.log 2>&1
```

> On some systems Poetry is at `~/.local/bin/poetry` — adjust path accordingly.

### Linux: systemd user timer (alternative)

Create `~/.config/systemd/user/get-rates-app.service`:

```ini
[Unit]
Description=Fetch Riksbank FX rates (group 130)

[Service]
Type=oneshot
WorkingDirectory=/absolute/path/to/repo
ExecStart=/usr/bin/env poetry run get-rates-app
```

Create `~/.config/systemd/user/get-rates-app.timer`:

```ini
[Unit]
Description=Daily run of get-rates-app

[Timer]
OnCalendar=08:00
Persistent=true

[Install]
WantedBy=default.target
```

Enable:

```bash
systemctl --user daemon-reload
systemctl --user enable --now get-rates-app.timer
systemctl --user status get-rates-app.timer
```

### Windows: Task Scheduler

Create a **Basic Task**:

* Trigger: Daily 08:00
* Action: *Start a program*
  Program/script:

  ```
  C:\Users\<you>\AppData\Roaming\Python\Scripts\poetry.exe
  ```

  Arguments:

  ```
  run get-rates-app
  ```

  Start in:

  ```
  C:\absolute\path\to\repo
  ```

> If Poetry is elsewhere (e.g., inside `C:\Users\<you>\.local\bin`), adjust the Program path.

---

## Formatting (black)

This repo uses **black** for formatting.

Format everything:

```bash
poetry run black .
```

---


## Notes

* Local SQLite DB is **not** committed (`.data/` is in `.gitignore`).
* The app is idempotent and safe to rerun; existing `(series_id, obs_date)` rows are updated.
* Feel free to fork and add tests (e.g., smoke test for JSON shape, DB write/read).

