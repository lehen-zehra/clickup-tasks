# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Setup

1. Copy `.env.example` to `.env` and set `CLICKUP_API_TOKEN` and `CLICKUP_LIST_ID`.
2. Install dependencies: `pip install -r requirements.txt`

## Commands

```bash
python main.py setup              # Browse workspace to find list ID and member IDs
python main.py create             # Interactively create a single task
python main.py batch data/tasks.json   # Bulk-create tasks from JSON
python main.py batch data/tasks.csv    # Bulk-create tasks from CSV
```

## Architecture

Two files:

- **`clickup_client.py`** — thin wrapper around the ClickUp v2 REST API. `ClickUpClient` holds an authenticated `requests.Session`. All API calls go through `_get`/`_post`. `PRIORITY_MAP` converts label strings (`urgent/high/normal/low`) to the numeric values ClickUp expects (1–4).

- **`main.py`** — CLI entry point. Reads `CLICKUP_API_TOKEN` and `CLICKUP_LIST_ID` from env. Three commands: `setup` (workspace browser), `create` (interactive), `batch` (JSON or CSV file). Priority resolution and date parsing (`parse_due_date`) happen in `main.py` before calling the client.

## Batch file format

Put task files in the `data/` folder (ignored by git — real data stays local). Examples are tracked at `data/example_tasks.json` and `data/example_tasks.csv`.

**JSON** — array of task objects (or `{"tasks": [...]}` wrapper):
```json
[{"name": "...", "priority": "high", "due_date": "2026-04-10", "assignees": [], "tags": ["backend"]}]
```

**CSV** — columns: `name, description, priority, due_date, assignees, tags`  
- `assignees`: comma-separated user IDs (integers)  
- `tags`: comma-separated strings  
- `due_date`: `YYYY-MM-DD`, `DD/MM/YYYY`, or `MM/DD/YYYY`
