"""ClickUp API client wrapper."""

import requests


BASE_URL = "https://api.clickup.com/api/v2"

PRIORITY_MAP = {
    "urgent": 1,
    "high": 2,
    "normal": 3,
    "low": 4,
}


class ClickUpClient:
    def __init__(self, api_token: str):
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": api_token,
            "Content-Type": "application/json",
        })

    def _get(self, path: str, params: dict = None):
        resp = self.session.get(f"{BASE_URL}{path}", params=params)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, body: dict):
        resp = self.session.post(f"{BASE_URL}{path}", json=body)
        resp.raise_for_status()
        return resp.json()

    def get_workspaces(self):
        return self._get("/team")["teams"]

    def get_spaces(self, team_id: str):
        return self._get(f"/team/{team_id}/space", {"archived": "false"})["spaces"]

    def get_folders(self, space_id: str):
        return self._get(f"/space/{space_id}/folder", {"archived": "false"})["folders"]

    def get_folderless_lists(self, space_id: str):
        return self._get(f"/space/{space_id}/list", {"archived": "false"})["lists"]

    def get_lists(self, folder_id: str):
        return self._get(f"/folder/{folder_id}/list", {"archived": "false"})["lists"]

    def get_members(self, list_id: str):
        """Get members from a list's tasks assignees pool via the list endpoint."""
        data = self._get(f"/list/{list_id}")
        return data.get("members", [])

    def get_workspace_members(self, team_id: str):
        spaces = self._get(f"/team/{team_id}/space", {"archived": "false"})["spaces"]
        members = {}
        for space in spaces:
            space_detail = self._get(f"/space/{space['id']}")
            for m in space_detail.get("members", []):
                user = m.get("user", m)
                uid = user.get("id")
                if uid:
                    members[uid] = user
        return list(members.values())

    def create_task(self, list_id: str, task: dict):
        """
        task keys: name (required), description, priority (1-4 or label),
                   assignees (list of user IDs), due_date (unix ms), tags (list of str)
        """
        body = {"name": task["name"]}

        if task.get("description"):
            body["description"] = task["description"]

        priority = task.get("priority")
        if priority is not None:
            if isinstance(priority, str):
                priority = PRIORITY_MAP.get(priority.lower())
            if priority:
                body["priority"] = priority

        if task.get("assignees"):
            body["assignees"] = task["assignees"]

        if task.get("due_date"):
            body["due_date"] = task["due_date"]

        if task.get("tags"):
            body["tags"] = task["tags"]

        if task.get("parent"):
            body["parent"] = task["parent"]

        return self._post(f"/list/{list_id}/task", body)
