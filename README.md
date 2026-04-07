# ClickUp Task Automation

A small CLI tool to create ClickUp tasks interactively or in bulk from a JSON/CSV file.

## Setup

**1. Clone the repo**
```bash
git clone <repo-url>
cd clickup-tasks
```

**2. Install dependencies**
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**3. Configure credentials**

Copy `.env.example` to `.env` and fill in your values:
```bash
cp .env.example .env
```

| Variable | How to get it |
|---|---|
| `CLICKUP_API_TOKEN` | ClickUp → Settings → Apps → API Token |
| `CLICKUP_LIST_ID` | Run `python main.py setup` to browse and find it |

## Commands

```bash
python main.py setup              # Browse your workspace to find list/member IDs
python main.py create             # Interactively create a single task
python main.py batch data/tasks.json   # Bulk-create tasks from a JSON file
python main.py batch data/tasks.csv    # Bulk-create tasks from a CSV file
```

## Batch file format

### JSON

An array of task objects. Subtasks can be nested:

```json
[
  {
    "name": "Set up CI/CD pipeline",
    "description": "Configure GitHub Actions for staging.",
    "priority": "high",
    "due_date": "2026-04-10",
    "tags": ["devops"],
    "subtasks": [
      { "name": "Add lint step", "priority": "normal" },
      { "name": "Add test step", "priority": "normal" }
    ]
  }
]
```

### CSV

Columns: `name, description, priority, due_date, assignees, tags, parent`

- `priority` — `urgent`, `high`, `normal`, or `low`
- `due_date` — `YYYY-MM-DD`, `DD/MM/YYYY`, or `MM/DD/YYYY`
- `assignees` — comma-separated user IDs (find them with `python main.py setup`)
- `tags` — comma-separated strings
- `parent` — name of another task in the same file to nest under

See `data/example_tasks.csv` and `data/example_tasks.json` for working examples.
