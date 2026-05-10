#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from clawqueue.config import load_config  # noqa: E402

DEFAULT_LABELS = {
    "cq:artifact": ("5319E7", "CQ deliverable: Markdown/report/document artifact; avoid product/source changes unless explicit"),
    "cq:change": ("0E8A16", "CQ deliverable: source/content/config change with verification evidence"),
    "cq:paused": ("BFD4F2", "CQ managed: paused until /cq retry"),
    "cq:failed": ("D73A4A", "CQ managed: failed and held until /cq retry"),
    "cq:blocked": ("FBCA04", "CQ managed: blocked and held until /cq retry"),
    "ceo": ("6F42C1", "CQ mode: strategy, prioritization, scope challenge"),
    "cto": ("1D76DB", "CQ mode: architecture and technical execution"),
    "cmo": ("D876E3", "CQ mode: growth, narrative, marketing, demand"),
    "researcher": ("0366D6", "CQ mode: evidence gathering and synthesis"),
    "reviewer": ("5319E7", "CQ mode: review completed agent work"),
    "dev": ("0E8A16", "CQ mode: implementation"),
    "engineer": ("0E8A16", "CQ mode: implementation"),
}
REQUIRED_STATUS_ALIASES = {
    "Todo": {"todo"},
    "In Progress": {"in progress", "in progress"},
    "Review": {"review", "in review"},
    "Done": {"done"},
}


def run(cmd: str) -> tuple[str, int]:
    proc = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    return (proc.stdout + proc.stderr).strip(), proc.returncode


def ensure_label(repo: str, name: str, color: str, description: str, dry_run: bool) -> None:
    cmd = (
        f"gh label create {shlex.quote(name)} --repo {shlex.quote(repo)} "
        f"--color {shlex.quote(color)} --description {shlex.quote(description)} --force"
    )
    if dry_run:
        print(f"DRY label {repo}: {name}")
        return
    out, rc = run(cmd)
    print(("✅" if rc == 0 else "⚠️"), f"label {repo}: {name}", out if rc else "")


def project_status_options(project_id: str) -> tuple[str, list[str]]:
    query = f'''query {{ node(id: "{project_id}") {{ ... on ProjectV2 {{ title fields(first: 20) {{ nodes {{ ... on ProjectV2SingleSelectField {{ name options {{ name }} }} }} }} }} }} }}'''
    out, rc = run(f"gh api graphql -f query={shlex.quote(query)}")
    if rc != 0:
        return "", []
    data = json.loads(out)
    node = data.get("data", {}).get("node") or {}
    for field in (node.get("fields") or {}).get("nodes") or []:
        if field.get("name") == "Status":
            return node.get("title", ""), [opt.get("name", "") for opt in field.get("options", [])]
    return node.get("title", ""), []


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap/validate CQ GitHub labels and ProjectV2 board shape for a selected CQ profile.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--profile", help="profile name under profiles/ to load, e.g. example or clawqueuehq")
    args = parser.parse_args()

    cfg = load_config(profile=args.profile)
    if cfg.profile_name:
        print(f"Profile: {cfg.profile_name}")
    else:
        print("Profile: none (built-in defaults)")

    repos = cfg.all_issue_repos()
    for repo in repos:
        for name, (color, description) in DEFAULT_LABELS.items():
            ensure_label(repo, name, color, description, args.dry_run)

    for key, project in cfg.projects.items():
        if not project.project_id:
            print(f"⚠️ project {key}: no project_id configured")
            continue
        title, statuses = project_status_options(project.project_id)
        normalized = {status.strip().lower() for status in statuses}
        missing = [name for name, aliases in REQUIRED_STATUS_ALIASES.items() if not (normalized & aliases)]
        if missing:
            print(f"⚠️ project {key} ({title}): missing status columns/options: {', '.join(missing)}")
            print("   GitHub ProjectV2 status options cannot be safely normalized without preserving option IDs; add them in the UI, then update workflow_policy.md.")
        else:
            print(f"✅ project {key} ({title}): canonical statuses present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
