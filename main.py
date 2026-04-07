#!/usr/bin/env python3
"""
ClickUp Task Automation Tool
Helps a PM create ClickUp tasks from tech lead input — interactively or via batch file.

Usage:
  python main.py setup              # Browse workspace and find your list ID
  python main.py create             # Interactively create a single task
  python main.py batch tasks.json   # Create multiple tasks from a JSON file
  python main.py batch tasks.csv    # Create multiple tasks from a CSV file
"""

import csv
import json
import os
import sys
from datetime import datetime

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from clickup_client import ClickUpClient, PRIORITY_MAP

load_dotenv()
console = Console()


# ── helpers ──────────────────────────────────────────────────────────────────

def get_client() -> ClickUpClient:
    token = os.getenv("CLICKUP_API_TOKEN", "")
    if not token or token == "pk_your_token_here":
        console.print("[red]Error:[/] CLICKUP_API_TOKEN not set. Copy .env.example to .env and fill it in.")
        sys.exit(1)
    return ClickUpClient(token)


def get_default_list_id() -> str:
    list_id = os.getenv("CLICKUP_LIST_ID", "")
    if not list_id or list_id == "your_list_id_here":
        console.print("[red]Error:[/] CLICKUP_LIST_ID not set. Run [bold]python main.py setup[/] first.")
        sys.exit(1)
    return list_id


def parse_due_date(value: str) -> int | None:
    """Accept YYYY-MM-DD or DD/MM/YYYY and return Unix ms."""
    if not value.strip():
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            dt = datetime.strptime(value.strip(), fmt)
            return int(dt.timestamp() * 1000)
        except ValueError:
            continue
    console.print(f"[yellow]Warning:[/] Could not parse date '{value}', skipping.")
    return None


def print_task_result(task: dict):
    url = task.get("url", "")
    tid = task.get("id", "")
    name = task.get("name", "")
    console.print(f"  [green]✓[/] [bold]{name}[/]  →  [cyan]{url or tid}[/]")


# ── commands ─────────────────────────────────────────────────────────────────

def cmd_setup():
    """Browse the workspace so the PM can find their list ID."""
    client = get_client()

    console.print(Panel("[bold]ClickUp Workspace Browser[/]", subtitle="Find your List ID"))

    workspaces = client.get_workspaces()
    if not workspaces:
        console.print("[red]No workspaces found for this token.[/]")
        return

    # Pick workspace
    ws_table = Table("Index", "Workspace", "ID")
    for i, ws in enumerate(workspaces):
        ws_table.add_row(str(i), ws["name"], ws["id"])
    console.print(ws_table)

    ws_idx = int(Prompt.ask("Select workspace index", default="0"))
    workspace = workspaces[ws_idx]
    team_id = workspace["id"]

    # Spaces
    spaces = client.get_spaces(team_id)
    sp_table = Table("Index", "Space", "ID")
    for i, sp in enumerate(spaces):
        sp_table.add_row(str(i), sp["name"], sp["id"])
    console.print(sp_table)

    sp_idx = int(Prompt.ask("Select space index", default="0"))
    space = spaces[sp_idx]
    space_id = space["id"]

    # Folders + folderless lists
    folders = client.get_folders(space_id)
    folderless = client.get_folderless_lists(space_id)

    all_lists = []

    if folders:
        console.print("\n[bold]Folders:[/]")
        for folder in folders:
            lists = client.get_lists(folder["id"])
            for lst in lists:
                all_lists.append(lst)

    for lst in folderless:
        all_lists.append(lst)

    lst_table = Table("Index", "List", "ID", "Folder")
    for i, lst in enumerate(all_lists):
        folder_name = lst.get("folder", {}).get("name", "—")
        lst_table.add_row(str(i), lst["name"], lst["id"], folder_name)
    console.print(lst_table)

    lst_idx = int(Prompt.ask("Select list index for default task creation", default="0"))
    chosen = all_lists[lst_idx]

    console.print(f"\n[green]Add this to your .env file:[/]")
    console.print(f"  CLICKUP_LIST_ID={chosen['id']}")

    # Show members
    members = client.get_workspace_members(team_id)
    console.print(f"\n Members in this workspace: {len(members)}")
    if members:
        console.print("\n[bold]Workspace members[/] (use IDs when assigning tasks):")
        m_table = Table("ID", "Username", "Email")
        for m in members:
            m_table.add_row(str(m.get("id", "")), m.get("username", ""), m.get("email", ""))
        console.print(m_table)


def cmd_create():
    """Interactively create a single task."""
    client = get_client()
    list_id = get_default_list_id()

    console.print(Panel("[bold]Create a ClickUp Task[/]", subtitle=f"List ID: {list_id}"))

    name = Prompt.ask("[bold]Task name[/]")
    description = Prompt.ask("Description [dim](optional)[/]", default="")
    priority_str = Prompt.ask(
        "Priority [dim](urgent/high/normal/low)[/]",
        choices=["urgent", "high", "normal", "low", ""],
        default="normal",
    )
    due_date_str = Prompt.ask("Due date [dim](YYYY-MM-DD, optional)[/]", default="")
    assignees_str = Prompt.ask("Assignee user IDs [dim](comma-separated, optional)[/]", default="")
    tags_str = Prompt.ask("Tags [dim](comma-separated, optional)[/]", default="")

    task = {
        "name": name,
        "description": description,
        "priority": priority_str or None,
        "due_date": parse_due_date(due_date_str),
        "assignees": [int(a.strip()) for a in assignees_str.split(",") if a.strip()],
        "tags": [t.strip() for t in tags_str.split(",") if t.strip()],
    }

    if Confirm.ask(f"\nCreate task [bold]{name}[/]?"):
        result = client.create_task(list_id, task)
        print_task_result(result)
        _ask_subtasks_interactive(client, list_id, result["id"], name)


def _ask_subtasks_interactive(client: "ClickUpClient", list_id: str, parent_id: str, parent_name: str, depth: int = 0):
    """Recursively prompt for subtasks after a task is created."""
    pad = "  " * (depth + 1)
    while Confirm.ask(f"{pad}Add a subtask to [bold]{parent_name}[/]?", default=False):
        sub_name = Prompt.ask(f"{pad}  Subtask name")
        sub_priority = Prompt.ask(
            f"{pad}  Priority [dim](urgent/high/normal/low)[/]",
            choices=["urgent", "high", "normal", "low", ""],
            default="",
        )
        sub_due = Prompt.ask(f"{pad}  Due date [dim](YYYY-MM-DD, optional)[/]", default="")
        subtask = {
            "name": sub_name,
            "priority": sub_priority or None,
            "due_date": parse_due_date(sub_due),
            "parent": parent_id,
        }
        sub_result = client.create_task(list_id, subtask)
        console.print(f"{pad}  ", end="")
        print_task_result(sub_result)
        _ask_subtasks_interactive(client, list_id, sub_result["id"], sub_name, depth + 1)


def _batch_create_json(client: "ClickUpClient", list_id: str, raw_tasks: list, parent_id: str | None,
                       created_by_name: dict, indent: str = "  ") -> tuple[int, int]:
    """Recursively create tasks from raw JSON dicts. Returns (success, failed)."""
    success, failed = 0, 0
    for raw in raw_tasks:
        if not raw.get("name", "").strip():
            console.print(f"{indent}[yellow]Skipping task with no name.[/]")
            failed += 1
            continue
        subtasks_raw = raw.pop("subtasks", [])
        task = _prepare_task(raw)
        if parent_id:
            task["parent"] = parent_id
        try:
            result = client.create_task(list_id, task)
            console.print(indent, end="")
            print_task_result(result)
            created_by_name[task["name"]] = result["id"]
            success += 1
            if subtasks_raw:
                s, f = _batch_create_json(client, list_id, subtasks_raw, result["id"], created_by_name, indent + "  ")
                success += s
                failed += f
        except Exception as e:
            console.print(f"{indent}[red]✗[/] [bold]{raw.get('name')}[/] — {e}")
            failed += 1
    return success, failed


def _prepare_task(row: dict) -> dict:
    """Normalise a raw task dict (from JSON or CSV) into a clean task dict."""
    task = {"name": row.get("name", "").strip()}
    if row.get("description"):
        task["description"] = str(row["description"]).strip()
    if row.get("priority"):
        p = str(row["priority"]).strip().lower()
        task["priority"] = PRIORITY_MAP.get(p, p)
    if row.get("due_date"):
        due = row["due_date"]
        task["due_date"] = due if isinstance(due, int) else parse_due_date(str(due))
    if row.get("assignees"):
        raw = row["assignees"]
        if isinstance(raw, list):
            task["assignees"] = [int(a) for a in raw if str(a).strip()]
        else:
            task["assignees"] = [int(a.strip()) for a in str(raw).split(",") if a.strip()]
    if row.get("tags"):
        raw = row["tags"]
        if isinstance(raw, list):
            task["tags"] = [str(t).strip() for t in raw if str(t).strip()]
        else:
            task["tags"] = [t.strip() for t in str(raw).split(",") if t.strip()]
    return task


def cmd_batch(filepath: str):
    """Create tasks from a JSON or CSV file."""
    client = get_client()
    list_id = get_default_list_id()

    if not os.path.exists(filepath):
        console.print(f"[red]File not found:[/] {filepath}")
        sys.exit(1)

    ext = os.path.splitext(filepath)[1].lower()

    created_by_name: dict[str, str] = {}  # task name → ClickUp task ID
    success, failed = 0, 0

    if ext == ".json":
        with open(filepath) as f:
            data = json.load(f)
        raw_list = data if isinstance(data, list) else data.get("tasks", [])
        console.print(Panel(f"[bold]Batch creating {len(raw_list)} top-level task(s)[/]", subtitle=f"List ID: {list_id}"))
        success, failed = _batch_create_json(client, list_id, raw_list, None, created_by_name)

    elif ext == ".csv":
        tasks = []
        with open(filepath, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                task = _prepare_task(row)
                if row.get("parent"):
                    task["_parent_name"] = row["parent"].strip()
                tasks.append(task)

        console.print(Panel(f"[bold]Batch creating {len(tasks)} task(s)[/]", subtitle=f"List ID: {list_id}"))

        for task in tasks:
            if not task.get("name"):
                console.print("[yellow]Skipping task with no name.[/]")
                failed += 1
                continue
            try:
                parent_name = task.pop("_parent_name", None)
                if parent_name:
                    parent_id = created_by_name.get(parent_name)
                    if not parent_id:
                        console.print(f"  [yellow]⚠[/] Parent '{parent_name}' not found for [bold]{task['name']}[/], creating as top-level.")
                    else:
                        task["parent"] = parent_id

                result = client.create_task(list_id, task)
                print_task_result(result)
                created_by_name[task["name"]] = result["id"]
                success += 1
            except Exception as e:
                console.print(f"  [red]✗[/] [bold]{task.get('name')}[/] — {e}")
                failed += 1
    else:
        console.print("[red]Unsupported file type.[/] Use .json or .csv")
        sys.exit(1)

    console.print(f"\n[green]{success} created[/], [red]{failed} failed[/]")


# ── entry point ───────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]

    if not args or args[0] in ("-h", "--help"):
        console.print(__doc__)
        return

    command = args[0]

    if command == "setup":
        cmd_setup()
    elif command == "create":
        cmd_create()
    elif command == "batch":
        if len(args) < 2:
            console.print("[red]Usage:[/] python main.py batch <file.json|file.csv>")
            sys.exit(1)
        cmd_batch(args[1])
    else:
        console.print(f"[red]Unknown command:[/] {command}")
        console.print("Run [bold]python main.py --help[/] for usage.")
        sys.exit(1)


if __name__ == "__main__":
    main()
