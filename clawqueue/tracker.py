from __future__ import annotations

import json
import shlex
from dataclasses import dataclass
from typing import Optional

from .config import ProjectConfig, RuntimeConfig
from .progress import PROGRESS_MARKER
from .shell import run_cmd


@dataclass(frozen=True)
class Task:
    number: int
    title: str
    body: str
    labels: list[str]
    mode_label: str
    agent_name: str
    priority: int
    repo: str
    project_name: str = ""
    deliverable_type: str = "change"
    author: str = ""


class TrackerClient:
    def __init__(self, config: RuntimeConfig):
        self.config = config
        self._board_cache: Optional[dict[str, dict]] = None

    @staticmethod
    def cache_key(repo: str, number: int) -> str:
        return f"{repo}:{number}"

    def project_has_board_ids(self, project: ProjectConfig) -> bool:
        return bool(project.project_id and project.field_id)

    def build_board_cache(self) -> dict[str, dict]:
        if self._board_cache is not None:
            return self._board_cache

        cache: dict[str, dict] = {}
        for proj_name, project in self.config.projects.items():
            if not self.project_has_board_ids(project):
                continue
            cursor: Optional[str] = None
            while True:
                after_arg = f', after: "{cursor}"' if cursor else ""
                query = f"""{{
                  node(id: "{project.project_id}") {{
                    ... on ProjectV2 {{
                      items(first: 100{after_arg}) {{
                        pageInfo {{ hasNextPage endCursor }}
                        nodes {{
                          id
                          statusField: fieldValueByName(name: "Status") {{
                            ... on ProjectV2ItemFieldSingleSelectValue {{ name }}
                          }}
                          priorityField: fieldValueByName(name: "Priority") {{
                            ... on ProjectV2ItemFieldSingleSelectValue {{ name }}
                          }}
                          content {{
                            ... on Issue {{ number repository {{ nameWithOwner }} }}
                          }}
                        }}
                      }}
                    }}
                  }}
                }}"""
                out, rc = run_cmd(
                    f"gh api graphql -f query={shlex.quote(query)}",
                    timeout=20,
                )
                if rc != 0:
                    break
                try:
                    items_data = json.loads(out)["data"]["node"]["items"]
                    items = items_data["nodes"]
                    page_info = items_data.get("pageInfo") or {}
                except (json.JSONDecodeError, KeyError, TypeError):
                    break
                for item in items:
                    content = item.get("content") or {}
                    number = content.get("number")
                    if not number:
                        continue
                    status_name = (item.get("statusField") or {}).get("name", "")
                    priority_name = (item.get("priorityField") or {}).get("name", "")
                    issue_repo = (
                        (content.get("repository") or {}).get("nameWithOwner") or project.repo
                    )
                    cache[self.cache_key(issue_repo, number)] = {
                        "project": proj_name,
                        "item_id": item["id"],
                        "status": status_name,
                        "priority": priority_name,
                    }
                if not page_info.get("hasNextPage"):
                    break
                cursor = page_info.get("endCursor")
                if not cursor:
                    break
        self._board_cache = cache
        return cache

    def invalidate_cache(self) -> None:
        self._board_cache = None

    def detect_target_project(self, title: str, labels: list[str]) -> str:
        # Keywords choose the project board; issue labels choose the agent mode.
        text = (title + " " + " ".join(labels)).lower()
        for project_name, keywords in self.config.project_routing_keywords.items():
            if any(keyword.lower() in text for keyword in keywords):
                return project_name
        if "CQC" in self.config.projects:
            return "CQC"
        return "MT"

    def add_to_project(
        self, issue_number: int, project_name: str, repo: str
    ) -> Optional[str]:
        project = self.config.projects.get(project_name)
        if not project or not self.project_has_board_ids(project):
            return None

        out, rc = run_cmd(
            f"gh issue view {issue_number} --repo {shlex.quote(repo)} --json id -q .id",
            timeout=10,
        )
        if rc != 0 or not out:
            return None

        mutation = f"""mutation {{
          addProjectV2ItemById(input: {{
            projectId: "{project.project_id}"
            contentId: "{out.strip()}"
          }}) {{ item {{ id }} }}
        }}"""
        out2, rc2 = run_cmd(f"gh api graphql -f query={shlex.quote(mutation)}", timeout=20)
        if rc2 != 0:
            return None
        try:
            item_id = json.loads(out2)["data"]["addProjectV2ItemById"]["item"]["id"]
        except (json.JSONDecodeError, KeyError, TypeError):
            return None

        cache = self.build_board_cache()
        cache[self.cache_key(repo, issue_number)] = {
            "project": project_name,
            "item_id": item_id,
            "status": "Todo",
            "priority": "",
        }
        print(f"📋 Added {repo}#{issue_number} to {project_name} board")
        return item_id

    def ensure_issue_in_project(
        self,
        issue_number: int,
        title: str,
        labels: list[str],
        repo: str,
    ) -> None:
        cache = self.build_board_cache()
        if self.cache_key(repo, issue_number) in cache:
            return
        target = self.detect_target_project(title, labels)
        item_id = self.add_to_project(issue_number, target, repo)
        if item_id:
            self.set_project_board_status(
                issue_number=issue_number,
                status_key="todo",
                title=title,
                labels=labels,
                repo=repo,
            )

    def set_project_board_status(
        self,
        issue_number: int,
        status_key: str,
        title: str,
        labels: list[str],
        repo: str,
    ) -> bool:
        cache = self.build_board_cache()
        entry = cache.get(self.cache_key(repo, issue_number))
        if entry:
            project_name = entry["project"]
            item_id = entry["item_id"]
        else:
            project_name = self.detect_target_project(title, labels)
            item_id = self.add_to_project(issue_number, project_name, repo)
            if not item_id:
                return False

        project = self.config.projects.get(project_name)
        if not project:
            return False
        option_id = project.status_options.get(status_key)
        if not option_id or not self.project_has_board_ids(project):
            print(
                f"⚠️ Missing board option config for {project_name}.{status_key}; "
                f"skipping status update for {repo}#{issue_number}"
            )
            return False

        mutation = f"""mutation {{
          updateProjectV2ItemFieldValue(input: {{
            projectId: "{project.project_id}"
            itemId: "{item_id}"
            fieldId: "{project.field_id}"
            value: {{ singleSelectOptionId: "{option_id}" }}
          }}) {{ projectV2Item {{ id }} }}
        }}"""
        out, rc = run_cmd(f"gh api graphql -f query={shlex.quote(mutation)}", timeout=20)
        ok = rc == 0 and "projectV2Item" in out
        if ok:
            cache[self.cache_key(repo, issue_number)]["status"] = project.status_name(status_key)
        print(
            f"📋 Board [{project_name}]: {repo}#{issue_number} → "
            f"{project.status_name(status_key)}"
        )
        return ok

    def list_issues(self, state: str = "open") -> list[dict]:
        issues: list[dict] = []
        for repo in self.config.all_issue_repos():
            path = f"repos/{repo}/issues?state={state}&per_page=100"
            out, rc = run_cmd(
                f"gh api --paginate --slurp {shlex.quote(path)}",
                timeout=20,
            )
            if rc != 0 or not out:
                continue
            try:
                pages = json.loads(out)
            except json.JSONDecodeError:
                continue
            if not isinstance(pages, list):
                continue
            for page in pages:
                if not isinstance(page, list):
                    continue
                for issue in page:
                    if not isinstance(issue, dict) or issue.get("pull_request"):
                        continue
                    normalized = {
                        "number": issue.get("number"),
                        "title": issue.get("title", ""),
                        "labels": issue.get("labels") or [],
                        "assignees": issue.get("assignees") or [],
                        "body": issue.get("body", ""),
                        "author": (issue.get("user") or {}).get("login", ""),
                        "state": issue.get("state", state),
                    }
                    if not normalized["number"]:
                        continue
                    normalized["_repo"] = repo
                    issues.append(normalized)
        return issues

    def list_open_issues(self) -> list[dict]:
        return self.list_issues("open")


    def reopen_issue(self, repo: str, issue_number: int) -> bool:
        out, rc = run_cmd(
            f"gh issue reopen {issue_number} --repo {shlex.quote(repo)}",
            timeout=20,
        )
        return rc == 0

    def issue_comments(self, repo: str, issue_number: int) -> list[dict]:
        out, rc = run_cmd(
            f"gh api --paginate --slurp repos/{shlex.quote(repo)}/issues/{issue_number}/comments",
            timeout=20,
        )
        if rc != 0 or not out:
            return []
        try:
            data = json.loads(out)
        except json.JSONDecodeError:
            return []
        if not isinstance(data, list):
            return []
        if data and all(isinstance(page, list) for page in data):
            return [comment for page in data for comment in page if isinstance(comment, dict)]
        return [comment for comment in data if isinstance(comment, dict)]

    def find_managed_comment_id(self, repo: str, issue_number: int, marker: str = PROGRESS_MARKER) -> Optional[int]:
        for comment in self.issue_comments(repo, issue_number):
            body = str(comment.get("body", ""))
            if marker in body:
                comment_id = comment.get("id")
                try:
                    return int(comment_id)
                except (TypeError, ValueError):
                    return None
        return None

    def upsert_managed_comment(self, repo: str, issue_number: int, body: str, marker: str = PROGRESS_MARKER) -> bool:
        comment_id = self.find_managed_comment_id(repo, issue_number, marker)
        if comment_id:
            payload = json.dumps({"body": body})
            out, rc = run_cmd(
                f"gh api repos/{shlex.quote(repo)}/issues/comments/{comment_id} "
                f"--method PATCH --input - <<'JSON'\n{payload}\nJSON",
                timeout=20,
            )
            return rc == 0
        return self.add_comment(repo, issue_number, body)

    def add_comment(self, repo: str, issue_number: int, body: str) -> bool:
        out, rc = run_cmd(
            f"gh issue comment {issue_number} --repo {shlex.quote(repo)} --body {shlex.quote(body)}",
            timeout=20,
        )
        return rc == 0

    def ensure_label(self, repo: str, name: str, color: str = "CFD3D7", description: str = "") -> None:
        run_cmd(
            f"gh label create {shlex.quote(name)} --repo {shlex.quote(repo)} "
            f"--color {shlex.quote(color)} --description {shlex.quote(description)} --force",
            timeout=10,
        )

    def add_label(self, repo: str, issue_number: int, name: str) -> None:
        self.ensure_label(repo, name, description="Managed by ClawQueue")
        run_cmd(
            f"gh issue edit {issue_number} --repo {shlex.quote(repo)} --add-label {shlex.quote(name)}",
            timeout=10,
        )

    def remove_label(self, repo: str, issue_number: int, name: str) -> None:
        run_cmd(
            f"gh issue edit {issue_number} --repo {shlex.quote(repo)} --remove-label {shlex.quote(name)}",
            timeout=10,
        )

    def close_issue(self, repo: str, issue_number: int, reason: str = "completed") -> bool:
        out, rc = run_cmd(
            f"gh issue close {issue_number} --repo {shlex.quote(repo)} --reason {shlex.quote(reason)}",
            timeout=20,
        )
        return rc == 0

    def get_issue_state(self, repo: str, issue_number: int) -> Optional[str]:
        out, rc = run_cmd(
            f"gh issue view {issue_number} --repo {shlex.quote(repo)} --json state -q .state",
            timeout=10,
        )
        if rc != 0:
            return None
        return out.strip()

    def get_issue_summary(self, repo: str, issue_number: int) -> dict:
        out, rc = run_cmd(
            f"gh issue view {issue_number} --repo {shlex.quote(repo)} "
            "--json title,body,labels,assignees,comments",
            timeout=15,
        )
        if rc != 0 or not out:
            return {}
        try:
            data = json.loads(out)
        except json.JSONDecodeError:
            return {}
        return data if isinstance(data, dict) else {}

    def add_assignee(self, repo: str, issue_number: int) -> None:
        if not self.config.github_assignee:
            return
        run_cmd(
            f"gh issue edit {issue_number} --repo {shlex.quote(repo)} "
            f"--add-assignee {shlex.quote(self.config.github_assignee)}",
            timeout=10,
        )

    def remove_assignee(self, repo: str, issue_number: int) -> None:
        if not self.config.github_assignee:
            return
        run_cmd(
            f"gh issue edit {issue_number} --repo {shlex.quote(repo)} "
            f"--remove-assignee {shlex.quote(self.config.github_assignee)}",
            timeout=10,
        )
