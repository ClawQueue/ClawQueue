#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DEFAULT_STATUSES = [
    "Todo",
    "In Progress",
    "Done",
]
STATUS_KEY_MAP = {
    "todo": "Todo",
    "in_progress": "In Progress",
    "done": "Done",
}


def run(cmd: str) -> tuple[str, int]:
    proc = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    return (proc.stdout + proc.stderr).strip(), proc.returncode


def gh_graphql(query: str, tolerate_partial_errors: bool = False) -> dict[str, Any]:
    out, rc = run(f"gh api graphql -f query={shlex.quote(query)}")
    if rc != 0:
        if tolerate_partial_errors and out:
            try:
                return json.loads(out)
            except json.JSONDecodeError:
                pass
        raise RuntimeError(out or "gh api graphql failed")
    return json.loads(out)


def owner_id(owner: str) -> str:
    org_query = f'''query {{ organization(login: "{owner}") {{ id }} }}'''
    try:
        data = gh_graphql(org_query).get("data", {})
        if data.get("organization"):
            return data["organization"]["id"]
    except Exception:
        pass

    user_query = f'''query {{ user(login: "{owner}") {{ id }} }}'''
    data = gh_graphql(user_query).get("data", {})
    if data.get("user"):
        return data["user"]["id"]
    raise RuntimeError(f"Could not resolve owner id for {owner}")


def create_project(owner: str, title: str) -> tuple[str, int, str]:
    oid = owner_id(owner)
    mutation = f'''mutation {{ createProjectV2(input: {{ ownerId: "{oid}", title: "{title}" }}) {{ projectV2 {{ id number title url }} }} }}'''
    data = gh_graphql(mutation)["data"]["createProjectV2"]["projectV2"]
    return data["id"], int(data["number"]), data["url"]


def project_fields(owner: str, number: int) -> list[dict[str, Any]]:
    out, rc = run(f"gh project field-list {number} --owner {shlex.quote(owner)} --format json")
    if rc != 0:
        raise RuntimeError(out or "gh project field-list failed")
    data = json.loads(out)
    return data.get("fields", data if isinstance(data, list) else [])


def ensure_status_field(owner: str, number: int) -> dict[str, Any]:
    fields = project_fields(owner, number)
    for field in fields:
        if field.get("name") == "Status":
            return field
    opts = ",".join(DEFAULT_STATUSES)
    out, rc = run(
        f"gh project field-create {number} --owner {shlex.quote(owner)} --name Status "
        f"--data-type SINGLE_SELECT --single-select-options {shlex.quote(opts)} --format json"
    )
    if rc != 0:
        raise RuntimeError(out or "gh project field-create failed")
    data = json.loads(out)
    if isinstance(data, dict) and data.get("name") == "Status":
        return data
    fields = project_fields(owner, number)
    for field in fields:
        if field.get("name") == "Status":
            return field
    raise RuntimeError("Status field was not created or could not be reloaded")


def link_project_to_repo(owner: str, number: int, repo: str) -> None:
    out, rc = run(f"gh project link {number} --owner {shlex.quote(owner)} --repo {shlex.quote(repo)}")
    if rc != 0 and "already linked" not in out.lower():
        raise RuntimeError(out or f"Could not link project to repo {repo}")


def policy_snippet(key: str, repo: str, project_id: str, field: dict[str, Any], number: int) -> dict[str, Any]:
    options = field.get("options") or []
    option_ids = {opt.get("name"): opt.get("id") for opt in options}
    status_options = {k: option_ids[v] for k, v in STATUS_KEY_MAP.items() if option_ids.get(v)}
    return {
        key: {
            "number": number,
            "repo": repo,
            "project_id": project_id,
            "field_id": field.get("id"),
            "status_options": status_options,
            "dispatch_statuses": ["Todo"],
        }
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Create a default CQ GitHub Project board and print policy IDs.")
    ap.add_argument("--owner", required=True, help="GitHub org or user that will own the project")
    ap.add_argument("--title", required=True, help="GitHub Project title")
    ap.add_argument("--key", required=True, help="CQ project key, e.g. CORE or GROWTH")
    ap.add_argument("--repo", required=True, help="Primary repo mapped to this project")
    args = ap.parse_args()

    try:
        project_id, number, url = create_project(args.owner, args.title)
        field = ensure_status_field(args.owner, number)
        link_project_to_repo(args.owner, number, args.repo)
    except Exception as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 1

    print(f"Created project: {args.title}")
    print(f"Owner: {args.owner}")
    print(f"Project number: {number}")
    print(f"Project id: {project_id}")
    print(f"URL: {url}")
    print(f"Status field id: {field.get('id')}")
    print(f"Linked repo: {args.repo}")
    print("\nDefault statuses:")
    for name in DEFAULT_STATUSES:
        print(f"- {name}")
    print("\nOptional manual UI upgrades for richer internal workflows:")
    print("- Inbox")
    print("- Review")
    print("- Blocked")
    print("\nPolicy snippet:")
    print(json.dumps(policy_snippet(args.key, args.repo, project_id, field, number), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
