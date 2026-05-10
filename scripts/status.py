#!/usr/bin/env python3
"""Show ClawQueue scheduler state and recent dispatch decisions."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Optional


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from clawqueue.config import ConfigError, RuntimeConfig, load_config
from clawqueue.tracker import TrackerClient


def load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return default


def pid_alive(pid: Optional[int]) -> bool:
    if not pid:
        return False
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, TypeError, ValueError):
        return False


def read_recent_decisions(path: Path, limit: int) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return []
    except OSError as exc:
        print(f"Could not read decision log: {exc}", file=sys.stderr)
        return []

    decisions: list[dict[str, Any]] = []
    for line in lines[-limit:]:
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            decisions.append(parsed)
    return decisions


def print_active_worker(config: RuntimeConfig) -> None:
    active = load_json(config.active_file, {})
    if not active:
        print("Active worker: none")
        return

    repo = active.get("repo", config.taskboard_repo)
    issue = active.get("issue", "?")
    pid = active.get("worker_pid")
    state = "alive" if pid_alive(pid) else "not running"
    print(f"Active worker: {repo}#{issue} pid={pid or '?'} ({state})")


def print_attempts(config: RuntimeConfig, limit: int) -> None:
    counts = load_json(config.attempt_count_file, {})
    if not counts:
        print("Attempts: none recorded")
        return

    ordered = sorted(counts.items(), key=lambda item: (-int(item[1]), item[0]))
    print(f"Attempts: showing {min(limit, len(ordered))} of {len(ordered)}")
    for key, count in ordered[:limit]:
        print(f"  {key}: {count}/{config.max_attempts_per_issue}")


def print_recent_decisions(config: RuntimeConfig, limit: int) -> None:
    decisions = read_recent_decisions(config.decision_log_file, limit)
    if not decisions:
        print("Recent decisions: none recorded")
        return

    print(f"Recent decisions: last {len(decisions)}")
    for entry in decisions:
        ts = str(entry.get("timestamp", "?")).replace("T", " ")
        decision = entry.get("decision", "?")
        reason = entry.get("reason", "")
        repo = entry.get("repo")
        issue = entry.get("issue")
        target = f" {repo}#{issue}" if repo and issue else ""
        print(f"  {ts} | {decision}{target} | {reason}")


def print_queue(config: RuntimeConfig, limit: int) -> None:
    tracker = TrackerClient(config)
    issues = tracker.list_open_issues()
    cache = tracker.build_board_cache()
    attempts = load_json(config.attempt_count_file, {})
    queued: list[tuple[str, int, str, str, int]] = []

    for issue in issues:
        repo = issue.get("_repo", config.taskboard_repo)
        number = int(issue["number"])
        if issue.get("assignees"):
            continue

        board_entry = cache.get(tracker.cache_key(repo, number))
        status = (board_entry or {}).get("status", "")
        project = config.projects.get((board_entry or {}).get("project", ""))
        dispatch_statuses = set(project.dispatch_statuses if project else ("Todo",))
        if status not in dispatch_statuses:
            continue

        attempt_count = int(attempts.get(f"{repo}:{number}", 0))
        if attempt_count >= config.max_attempts_per_issue:
            continue
        queued.append((status, number, repo, issue.get("title", ""), attempt_count))

    if not queued:
        print("Queued issues: none found or GitHub unavailable")
        return

    queued.sort(key=lambda item: (item[1], item[2]))
    print(f"Queued issues: showing {min(limit, len(queued))} of {len(queued)}")
    for status, number, repo, title, attempt_count in queued[:limit]:
        print(f"  [{status}] {repo}#{number} ({attempt_count}/{config.max_attempts_per_issue}) {title}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=10, help="rows to show per section")
    parser.add_argument(
        "--no-queue",
        action="store_true",
        help="skip GitHub queue lookup and show only local state",
    )
    parser.add_argument("--profile", help="profile name under profiles/ to load")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        config = load_config(profile=args.profile)
    except ConfigError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 2

    if config.profile_name:
        print(f"Profile: {config.profile_name} ({config.profile_dir})")
    else:
        print("Profile: none (built-in defaults)")
    print(f"State dir: {config.state_dir}")
    artifact_repo = f" repo={config.artifact_repo}" if config.artifact_repo else ""
    artifact_checkout = (
        f" checkout={config.artifact_checkout_dir}" if config.artifact_backend == "git" else ""
    )
    print(
        f"Artifacts: backend={config.artifact_backend}{artifact_repo}{artifact_checkout} "
        f"path={config.artifact_path} commit={config.artifact_commit}"
    )
    print_active_worker(config)
    print_recent_decisions(config, args.limit)
    print_attempts(config, args.limit)
    if not args.no_queue:
        print_queue(config, args.limit)
    return 0


if __name__ == "__main__":
    sys.exit(main())
