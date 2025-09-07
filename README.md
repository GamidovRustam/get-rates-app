ось повний, самодостатній `README.md`, який можна покласти в репозиторій. Він покриває встановлення та запуск на **macOS / Linux / Windows**, форматування коду, запуск за розкладом і типові проблеми.

````markdown
# FX Rates (Riksbank SWEA → SQLite), Group 130

A tiny Python app that fetches **latest** FX rates for **group 130** from Riksbank SWEA API  
in a single request and stores them into a local SQLite database.

- API endpoint (single call):  
  `GET https://api.riksbank.se/swea/v1/Observations/Latest/ByGroup/130`
- Response format example:
```json
[
  {"seriesId":"SEKUSDPMI","date":"2025-09-05","value":9.40498},
  {"seriesId":"SEKEURPMI","date":"2025-09-05","value":11.001}
]
````

> The app writes each item as a row into `observations(series_id, obs_date, value, received_at)`,
> with a composite primary key `(series_id, obs_date)` to keep historical records without duplicates.

---

## Contents

* [Requirements](#requirements)
* [Install (macOS, Linux, Windows)](#install-macos-linux-windows)
* [Quick Start](#quick-start)
* [How It Works](#how-it-works)
* [Database & Queries](#database--queries)
* [Scheduling (cron / systemd / Task Scheduler)](#scheduling-cron--systemd--task-scheduler)
* [Formatting (black)](#formatting-black)
* [Troubleshooting](#troubleshooting)
* [Notes](#notes)
* [License](#license)

---

## Requirements

* **Python 3.10.8** (exact version)
* **Poetry** (dependency management & isolated virtualenv)
* Internet access to reach `api.riksbank.se`

> SQLite is part of Python’s standard library (`sqlite3`), no extra DB server required.

---

## Install (macOS, Linux, Windows)

### macOS (zsh)

1. **Install Python 3.10.8** (via `pyenv`, recommended)

```bash
# If Homebrew not installed:
# /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

brew update
brew install pyenv
echo 'eval "$(pyenv init -)"' >> ~/.zshrc
exec zsh

pyenv install 3.10.8
pyenv local 3.10.8    # run inside the repo folder
python -V             # should show 3.10.8
```

2. **Install Poetry**

```bash
curl -sSL https://install.python-poetry.org | python3 -
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
exec zsh
```

3. **Project deps**

```bash
poetry install
```

### Linux (bash)

1. **Install build deps** (example: Ubuntu/Debian)

```bash
sudo apt update
sudo apt install -y build-essential libssl-dev zlib1g-dev libbz2-dev \
  libreadline-dev libsqlite3-dev curl git libncursesw5-dev xz-utils \
  tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev
```

2. **Install Python 3.10.8 via pyenv**

```bash
curl https://pyenv.run | bash
# Add to shell:
echo 'export PATH="$HOME/.pyenv/bin:$PATH"' >> ~/.bashrc
echo 'eval "$(pyenv init -)"' >> ~/.bashrc
exec bash

pyenv install 3.10.8
pyenv local 3.10.8     # inside the repo
python -V
```

3. **Install Poetry**

```bash
curl -sSL https://install.python-poetry.org | python3 -
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
exec bash

poetry install
```

### Windows (PowerShell)

1. **Python 3.10.8**

   * Option A: install official Python 3.10.8 (ensure “Add to PATH”).
   * Option B (recommended for version pinning): install **pyenv-win**
     [https://github.com/pyenv-win/pyenv-win](https://github.com/pyenv-win/pyenv-win)

   With pyenv-win:

   ```powershell
   # In PowerShell as Admin (follow pyenv-win docs for installation):
   pyenv install 3.10.8
   pyenv local 3.10.8   # run inside the repo
   python --version
   ```

2. **Poetry**

```powershell
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | py - 
# If PATH not updated automatically:
$env:Path += ";$env:UserProfile\.local\bin"
poetry --version
poetry install
```

> If you hit issues with packaging mode in Poetry 2.x, either keep the provided `pyproject.toml` with `packages = [{ include = "app" }]`, or run `poetry install --no-root`.

---

## Quick Start

```bash
# In the repo root:
poetry install

# Run the app
poetry run fx-rates
# or
poetry run python app/main.py
```

This will:

* create `.data/fx_rates.sqlite3` if missing,
* apply SQL migration from `sql/001_init.sql`,
* fetch the latest observations for **group 130** in a single HTTP call,
* upsert rows into `observations`.

---

## How It Works

* The app calls **`/Observations/Latest/ByGroup/130`** once and receives a list of records:

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

* Count rows:

```sql
SELECT COUNT(*) AS rows_total FROM observations;
```

---

## Scheduling (cron / systemd / Task Scheduler)

Run **once a day** to keep history updated.

### macOS / Linux: cron

```bash
crontab -e
# Every day at 08:00 (local time)
0 8 * * * cd /absolute/path/to/repo && /usr/local/bin/poetry run fx-rates >> .data/cron.log 2>&1
```

> On some systems Poetry is at `~/.local/bin/poetry` — adjust path accordingly.

### Linux: systemd user timer (alternative)

Create `~/.config/systemd/user/fx-rates.service`:

```ini
[Unit]
Description=Fetch Riksbank FX rates (group 130)

[Service]
Type=oneshot
WorkingDirectory=/absolute/path/to/repo
ExecStart=/usr/bin/env poetry run fx-rates
```

Create `~/.config/systemd/user/fx-rates.timer`:

```ini
[Unit]
Description=Daily run of fx-rates

[Timer]
OnCalendar=08:00
Persistent=true

[Install]
WantedBy=default.target
```

Enable:

```bash
systemctl --user daemon-reload
systemctl --user enable --now fx-rates.timer
systemctl --user status fx-rates.timer
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
  run fx-rates
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

## Troubleshooting

* **`ModuleNotFoundError: No module named 'requests'`**
  Run `poetry install`. If `requests` is in `pyproject.toml` but not installed, also try:

  ```bash
  poetry install --no-root
  poetry run pip show requests
  ```

* **“The current project could not be installed … No file/folder found for package …” (Poetry 2.x)**
  You can either:

  1. Keep packaging mode (as in this repo) where `pyproject.toml` has
     `packages = [{ include = "app" }]`, or
  2. Run `poetry install --no-root`, or
  3. Set `package-mode = false` in `[tool.poetry]` if you prefer dependency-only mode.

* **Poetry not found in PATH**
  Ensure `~/.local/bin` (Linux/macOS) or `%UserProfile%\.local\bin` (Windows) is in PATH.

* **Corporate proxy / SSL issues**
  Export standard proxy vars before running:

  ```bash
  export HTTP_PROXY=http://proxy:port
  export HTTPS_PROXY=http://proxy:port
  poetry run fx-rates
  ```

* **Rate limits**
  We use a **single** API request for group 130, well within the documented 4 req/min limit.

---

## Notes

* Local SQLite DB is **not** committed (`.data/` is in `.gitignore`).
* The app is idempotent and safe to rerun; existing `(series_id, obs_date)` rows are updated.
* Feel free to fork and add tests (e.g., smoke test for JSON shape, DB write/read).

