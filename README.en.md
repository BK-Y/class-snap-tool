# Class Performance Quick Notes Tool

A Flask + SQLite classroom management prototype focused on student records and basic class management.

## Features

- Student list with filters (legal name, nickname, gender)
- Add student flow
- Basic class module entry
- Local SQLite storage with auto schema initialization

## Project Layout

```text
class-snap-tool/
├── dao/                # Data access layer
├── db/                 # DB connection and schema
├── web/                # Flask app, routes, templates
├── run.py              # Cross-platform startup entry (recommended)
├── requirements.txt
└── start.ps1           # Windows PowerShell startup script
```

## Requirements

- Python 3.10+
- pip
- Linux or Windows

## Setup

Run in project root:

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

### Windows (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

## Run (Recommended)

Use the same command on Linux/Windows:

```bash
python run.py
```

Optional arguments:

```bash
python run.py --host 0.0.0.0 --port 5001 --debug
```

Environment variables are also supported: `HOST`, `PORT`, `DEBUG`.

Open: <http://127.0.0.1:5000>

## Alternative Run Command

```bash
python -m web.app
```

## Troubleshooting

### Port 5000 already in use

- Stop old process: `pkill -f "python -m web.app"`
- Or run another port: `python run.py --port 5001`

### No `Scripts` directory on Linux

Expected platform difference:

- Windows: `.venv/Scripts/`
- Linux/macOS: `.venv/bin/`

## Development Notes

- Entrypoints: `run.py`, `web/app.py`
- Database schema: `db/schema.sql`
- First run auto-creates `.data/school.db`

## Contribution

1. Fork the repository
2. Create a branch (for example `feat/xxx`)
3. Commit your changes
4. Open a Pull Request
