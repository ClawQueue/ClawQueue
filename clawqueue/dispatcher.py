from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from typing import Optional

from .activity import ActivityMonitor
from .config import ConfigError, RuntimeConfig, load_config
from .deliverables import deliverable_label, resolve_deliverable_type
from .notifications import TelegramNotifier
from .progress import extract_result, progress_body
from .runner import COMPLETION_SENTINEL, AgentRunner
from .shell import run_cmd
from .tracker import Task, TrackerClient


class ClawQueueDispatcher:
    PRIORITY_ORDER = {"🔴 Urgent": 0, "🟡 Normal": 1, "": 2, "🔵 Low": 3}
    NON_PRIORITY_MODES = {"ceo", "cto", "dev", "engineer"}
    EXPLICIT_AGENT_PREFIX = "agent:"

    def __init__(self, config: RuntimeConfig):
        self.config = config
        self.activity = ActivityMonitor(config)
        self.tracker = TrackerClient(config)
        self.runner = AgentRunner(config, self.tracker)
        self.notifier = TelegramNotifier(config)

    def main(self) -> int:
        self.trim_decision_log()
        self.process_slash_commands()
        if self.reconcile_completed_active_task():
            self.log_decision("skip", "reconciled active task; dispatch deferred until next tick")
            return 0
        self.sweep_stale_in_progress()

        should_dispatch, reason = self.should_dispatch_now()
        if not should_dispatch:
            self.log_decision("skip", reason)
            return 0

        return self.dispatch_next_task()

    def should_dispatch_now(self) -> tuple[bool, str]:
        if self.check_lock():
            return False, "dispatcher lock is active"
        if self.worker_is_running():
            return False, "worker is already active"
        if self.check_throttle():
            return False, "scheduler throttle is active"
        return True, "ready"

    def dispatch_next_task(self) -> int:
        minutes_idle, _is_quiet = self.activity.get_last_user_activity()

        task = self.pick_review_task() or self.pick_task()
        if not task:
            self.log_decision("skip", "no eligible configured dispatch-status task")
            return 0

        ok, reason, agent_override, user_asked = self.should_work(minutes_idle, task)
        if not ok:
            prefix = "Asked user on Telegram" if user_asked else "Skipping"
            print(f"⏸ {prefix}: {reason}")
            self.log_decision(
                "skip",
                reason,
                task,
                {"user_asked": user_asked, "minutes_idle": round(minutes_idle, 2)},
            )
            return 0

        if agent_override:
            original = task.agent_name
            task = replace(task, agent_name=agent_override)
            print(f"🔄 Rerouted: {original} → {agent_override} (provider exhausted)")

        self.ensure_deliverable_label(task)

        safety_error = self.validate_task_safety(task)
        if safety_error:
            print(f"🚫 Safety blocker for #{task.number}: {safety_error}")
            self.mark_launch_blocked(task, safety_error, label="cq:blocked")
            self.log_decision("blocked", safety_error, task)
            return 0

        config_error = self.validate_task_agent(task)
        if config_error:
            print(f"🚫 Config blocker for #{task.number}: {config_error}")
            self.mark_launch_blocked(task, config_error)
            self.log_decision("blocked", config_error, task)
            return 0

        self.acquire_lock(task.repo, task.number)
        try:
            cache = self.tracker.build_board_cache()
            project_name = cache.get(self.tracker.cache_key(task.repo, task.number), {}).get(
                "project", "?"
            )
            print(
                f"🔥 Dispatching: #{task.number} [{project_name}] — {task.title} "
                f"[{task.mode_label} via {task.agent_name}]"
            )
            self.tracker.add_assignee(task.repo, task.number)
            self.tracker.set_project_board_status(
                task.number,
                "in_progress",
                task.title,
                task.labels,
                repo=task.repo,
            )
            worker_pid = self.runner.start_worker(task)
            if worker_pid is None:
                print(f"⚠️ Worker for #{task.number} failed on launch — unassigning for retry")
                self.log_decision("launch_failed", "worker failed immediately", task)
                self.tracker.remove_assignee(task.repo, task.number)
                self.tracker.set_project_board_status(
                    task.number,
                    "todo",
                    task.title,
                    task.labels,
                    repo=task.repo,
                )
                return 1
            attempt_n = self.increment_attempt_count(task.repo, task.number)
            print(f"   Attempt #{attempt_n} for {task.repo}#{task.number}")
            self.register_worker(task.number, worker_pid, repo=task.repo)
            self.record_run()
            self.log_decision(
                "dispatched",
                "worker started",
                task,
                {
                    "worker_pid": worker_pid,
                    "attempt": attempt_n,
                    "project": project_name,
                },
            )
        except Exception as exc:
            print(f"❌ Error starting worker: {exc}", file=sys.stderr)
            self.log_decision("error", str(exc), task)
            self.release_lock()
            return 1
        finally:
            self.release_lock()
        return 0

    def pick_review_task(self) -> Optional[Task]:
        issues = self.tracker.list_open_issues()
        if not issues:
            return None

        cache = self.tracker.build_board_cache()
        candidates: list[Task] = []
        for issue in issues:
            issue_number = issue["number"]
            issue_repo = issue.get("_repo", self.config.taskboard_repo)
            if issue.get("assignees"):
                continue
            if self.get_attempt_count(issue_repo, issue_number) >= self.config.max_attempts_per_issue:
                continue

            board_entry = cache.get(self.tracker.cache_key(issue_repo, issue_number))
            if not board_entry:
                continue
            project = self.config.projects.get(board_entry.get("project", ""))
            dispatch_statuses = set(project.dispatch_statuses if project else ("Todo",))
            review_statuses = {"Review", "In review"}
            if not (dispatch_statuses & review_statuses) or board_entry.get("status") not in review_statuses:
                continue

            labels = [
                label.get("name", "") if isinstance(label, dict) else str(label)
                for label in (issue.get("labels") or [])
            ]
            if {"cq:paused", "cq:failed", "cq:blocked"} & set(labels):
                continue
            candidates.append(
                Task(
                    number=issue_number,
                    title=issue["title"],
                    body=issue.get("body", ""),
                    labels=labels,
                    mode_label="reviewer",
                    agent_name=(self.config.resolve_agent_candidates("reviewer") or (self.config.mode_to_agent.get("reviewer", "reviewer"),))[0],
                    priority=0,
                    repo=issue_repo,
                    project_name=board_entry.get("project", ""),
                    deliverable_type=resolve_deliverable_type(labels, issue["title"], issue.get("body", "")),
                    author=issue.get("author", ""),
                )
            )

        if not candidates:
            return None

        def sort_key(task: Task) -> tuple[int, int]:
            board_entry = cache.get(self.tracker.cache_key(task.repo, task.number), {})
            board_priority = self.PRIORITY_ORDER.get(board_entry.get("priority", ""), 2)
            return (board_priority, task.number)

        candidates.sort(key=sort_key)
        return candidates[0]

    def completed_status_key(self, repo: str, number: int, summary: dict) -> str:
        labels = [label.get("name", "") for label in summary.get("labels", [])]
        comments = summary.get("comments") or []
        last_comment = self.latest_completion_comment(comments)

        cache = self.tracker.build_board_cache()
        entry = cache.get(self.tracker.cache_key(repo, number), {})
        project = self.config.projects.get(entry.get("project", ""))
        has_review_column = bool(project and "review" in project.status_options)
        has_done_comment = self.is_completion_comment(last_comment)
        if has_done_comment and self.has_retry_after_latest_completion(comments):
            return "todo"
        result = extract_result(last_comment) or {}
        result_status = result.get("status")
        needs_review = bool(result.get("needs_review"))
        review_labels = {"cto", "dev", "engineer"}
        if not has_done_comment:
            return "todo"
        if result_status in {"failed", "blocked"}:
            return "review" if has_review_column else "todo"
        if has_review_column and result_status == "done":
            return "review"
        if has_review_column and (needs_review or any(label in review_labels for label in labels)):
            return "review"
        return "done"

    @staticmethod
    def is_completion_comment(comment_body: str) -> bool:
        stripped = comment_body.lstrip()
        return COMPLETION_SENTINEL in comment_body or stripped.lower().startswith("done -")

    @classmethod
    def has_retry_after_latest_completion(cls, comments: list) -> bool:
        latest_completion_index: Optional[int] = None
        for index, comment in enumerate(comments):
            if not isinstance(comment, dict):
                continue
            if cls.is_completion_comment(str(comment.get("body", ""))):
                latest_completion_index = index
        if latest_completion_index is None:
            return False
        for index, comment in enumerate(comments[latest_completion_index + 1 :], latest_completion_index + 1):
            if not isinstance(comment, dict):
                continue
            if cls.extract_cq_command(str(comment.get("body", ""))) == "retry" and not cls.command_already_consumed("retry", comments, index):
                return True
        return False

    @classmethod
    def latest_completion_comment(cls, comments: list) -> str:
        for comment in reversed(comments):
            if not isinstance(comment, dict):
                continue
            body = str(comment.get("body", ""))
            if cls.is_completion_comment(body):
                return body
        return ""

    @staticmethod
    def dependency_issue_numbers(body: str) -> set[int]:
        numbers: set[int] = set()
        for match in re.finditer(r"depends?\s+on\s+(?:Issue\s+)?#(\d+)", body, flags=re.IGNORECASE):
            try:
                numbers.add(int(match.group(1)))
            except ValueError:
                pass
        return numbers

    def dependency_ready(self, repo: str, issue_number: int) -> bool:
        cache = self.tracker.build_board_cache()
        entry = cache.get(self.tracker.cache_key(repo, issue_number), {})
        if entry.get("status") == "Done":
            return True
        summary = self.tracker.get_issue_summary(repo, issue_number)
        comments = summary.get("comments") or []
        completion = self.latest_completion_comment(comments)
        return bool(completion and not self.has_retry_after_latest_completion(comments))

    def dependencies_ready(self, repo: str, issue_number: int, body: str) -> tuple[bool, list[int]]:
        blocked_by: list[int] = []
        for dependency in sorted(self.dependency_issue_numbers(body)):
            if dependency == issue_number:
                continue
            if not self.dependency_ready(repo, dependency):
                blocked_by.append(dependency)
        return (not blocked_by, blocked_by)

    def pick_task(self) -> Optional[Task]:
        active_issue_key = None
        if self.config.active_file.exists():
            try:
                active_data = json.loads(self.config.active_file.read_text())
                active_issue = active_data.get("issue")
                active_repo = active_data.get("repo", self.config.taskboard_repo)
                if active_issue:
                    active_issue_key = self.attempt_count_key(active_repo, active_issue)
            except (json.JSONDecodeError, OSError):
                pass

        issues = self.tracker.list_open_issues()
        if not issues:
            return None

        cache = self.tracker.build_board_cache()
        candidates: list[Task] = []
        for issue in issues:
            issue_number = issue["number"]
            issue_repo = issue.get("_repo", self.config.taskboard_repo)

            if active_issue_key and self.attempt_count_key(issue_repo, issue_number) == active_issue_key:
                continue
            if issue.get("assignees"):
                continue
            if self.get_attempt_count(issue_repo, issue_number) >= self.config.max_attempts_per_issue:
                continue

            board_entry = cache.get(self.tracker.cache_key(issue_repo, issue_number))
            if not board_entry:
                continue
            project = self.config.projects.get(board_entry.get("project", ""))
            dispatch_statuses = set(project.dispatch_statuses if project else ("Todo",))
            if board_entry.get("status") not in dispatch_statuses:
                continue

            labels = [
                label.get("name", "") if isinstance(label, dict) else str(label)
                for label in (issue.get("labels") or [])
            ]
            if {"cq:paused", "cq:failed", "cq:blocked"} & set(labels):
                continue
            ready, blocked_by = self.dependencies_ready(issue_repo, issue_number, issue.get("body", ""))
            if not ready:
                self.log_decision(
                    "skipped",
                    "waiting for dependencies: " + ", ".join(f"#{item}" for item in blocked_by),
                    extra={"repo": issue_repo, "issue": issue_number},
                )
                continue
            # Labels choose the cognitive mode; config resolves that role to one or more concrete agents.
            mode_label = self.runner.resolve_mode(labels)
            deliverable_type = resolve_deliverable_type(labels, issue["title"], issue.get("body", ""))
            explicit_agent = self.extract_explicit_agent(labels)
            agent_candidates = self.config.resolve_agent_candidates(mode_label, explicit_agent)
            agent_name = agent_candidates[0] if agent_candidates else self.config.mode_to_agent.get(mode_label, "cto")

            if mode_label in self.NON_PRIORITY_MODES:
                priority = 50
            else:
                try:
                    priority = list(self.config.mode_priority).index(mode_label)
                except ValueError:
                    priority = 50

            candidates.append(
                Task(
                    number=issue_number,
                    title=issue["title"],
                    body=issue.get("body", ""),
                    labels=labels,
                    mode_label=mode_label,
                    agent_name=agent_name,
                    priority=priority,
                    repo=issue_repo,
                    project_name=board_entry.get("project", ""),
                    deliverable_type=deliverable_type,
                    author=issue.get("author", ""),
                )
            )

        if not candidates:
            return None

        def sort_key(task: Task) -> tuple[int, int, int]:
            board_entry = cache.get(self.tracker.cache_key(task.repo, task.number), {})
            board_priority = self.PRIORITY_ORDER.get(board_entry.get("priority", ""), 2)
            return (board_priority, task.number, task.priority)

        candidates.sort(key=sort_key)
        picked = candidates[0]
        self.tracker.ensure_issue_in_project(
            picked.number,
            picked.title,
            picked.labels,
            repo=picked.repo,
        )
        return picked

    def ensure_deliverable_label(self, task: Task) -> None:
        expected = deliverable_label(task.deliverable_type)
        if expected not in {label.lower() for label in task.labels}:
            self.tracker.add_label(task.repo, task.number, expected)
            task.labels.append(expected)

    def extract_explicit_agent(self, labels: list[str]) -> str | None:
        for label in labels:
            if not label:
                continue
            lowered = label.strip().lower()
            if lowered.startswith(self.EXPLICIT_AGENT_PREFIX):
                agent = lowered[len(self.EXPLICIT_AGENT_PREFIX):].strip()
                if agent:
                    return agent
        return None

    def validate_task_safety(self, task: Task) -> str:
        if task.deliverable_type != "change":
            return ""
        allowlist = {author.lower() for author in getattr(self.config, "change_author_allowlist", ())}
        if not allowlist:
            return ""
        author = (task.author or "").lower()
        if author in allowlist:
            return ""
        if not author:
            return "cq:change is restricted, and CQ could not determine the GitHub issue author"
        allowed = ", ".join(sorted(allowlist))
        return f"cq:change is restricted to trusted GitHub authors ({allowed}); issue author is `{task.author}`"

    def validate_task_agent(self, task: Task) -> str:
        if self.config.runner_backend != "openclaw":
            return ""
        agents, agent_error = self.available_openclaw_agents()
        if agent_error:
            return ""
        if agents and task.agent_name not in agents:
            available = ", ".join(sorted(agents))
            candidates = self.config.resolve_agent_candidates(task.mode_label)
            if candidates:
                return (
                    f"OpenClaw agent `{task.agent_name}` is not configured for role `{task.mode_label}` "
                    f"(candidates: {', '.join(candidates)}; available: {available})"
                )
            return (
                f"OpenClaw agent `{task.agent_name}` is not configured "
                f"(available: {available})"
            )
        return ""

    def mark_launch_blocked(self, task: Task, reason: str, label: str = "cq:failed") -> None:
        self.tracker.remove_assignee(task.repo, task.number)
        self.tracker.add_label(task.repo, task.number, label)
        cache = self.tracker.build_board_cache()
        project_name = cache.get(self.tracker.cache_key(task.repo, task.number), {}).get("project", "")
        project = self.config.projects.get(project_name)
        if project and "review" in project.status_options:
            self.tracker.set_project_board_status(
                task.number,
                "review",
                task.title,
                task.labels,
                repo=task.repo,
            )
        self.tracker.upsert_managed_comment(
            task.repo,
            task.number,
            progress_body(
                status="blocked" if label == "cq:blocked" else "failed",
                repo=task.repo,
                issue=task.number,
                title=task.title,
                details=[
                    f"Launch blocked before dispatch: {reason}",
                    f"CQ added `{label}` so the scheduler will not keep retrying this issue.",
                    "Fix the blocker, then use `/cq retry`.",
                ],
            ),
        )

    def check_quota_and_route(self, task: Task) -> tuple[bool, str, Optional[str]]:
        agent_name = task.agent_name
        primary_provider = self.config.agent_provider.get(agent_name, "claude")
        ok, reason = self.provider_has_quota(primary_provider)
        if ok:
            return True, reason, None

        fallback_agent = self.config.agent_fallback.get(agent_name)
        if not fallback_agent:
            return False, reason, None

        fallback_provider = self.config.agent_provider.get(fallback_agent, "claude")
        fallback_ok, fallback_reason = self.provider_has_quota(fallback_provider)
        if fallback_ok:
            print(
                f"🔄 {primary_provider} exhausted ({reason}) → rerouting "
                f"{agent_name} → {fallback_agent} ({fallback_provider})"
            )
            return True, f"rerouted: {reason} → using {fallback_agent}", fallback_agent
        return False, f"both providers exhausted: {reason} | fallback: {fallback_reason}", None

    def should_work(
        self, minutes_idle: float, task: Task
    ) -> tuple[bool, str, Optional[str], bool]:
        if self.config.user_active_gate_min > 0 and minutes_idle < self.config.user_active_gate_min:
            asked = self.notifier.ask_user_permission(task)
            return (
                False,
                f"user active ({minutes_idle:.1f}min idle < {self.config.user_active_gate_min}min gate)",
                None,
                asked,
            )
        if self.config.idle_timeout_min > 0 and minutes_idle < self.config.idle_timeout_min:
            return (
                False,
                f"user active ({minutes_idle:.1f}min idle < {self.config.idle_timeout_min}min idle timeout)",
                None,
                False,
            )
        ok, reason, agent_override = self.check_quota_and_route(task)
        if not ok:
            return False, reason, None, False
        return True, reason, agent_override, False

    def get_codexbar_usage(self, provider: str) -> Optional[dict]:
        provider = provider.lower()
        if provider == "local":
            return {"primary": {"usedPercent": 0}, "plan": "local"}

        if provider == "claude":
            cmd = f"codexbar usage --provider {provider} --no-credits --format json"
        else:
            cmd = f"codexbar usage --provider {provider} --source cli --no-credits --format json"
        out, rc = run_cmd(cmd, timeout=30)
        if rc != 0 or not out:
            return None
        try:
            data = json.loads(out)
        except json.JSONDecodeError:
            return None
        if not data or not isinstance(data, list):
            return None
        entry = data[0]
        if not isinstance(entry, dict) or "error" in entry:
            return None
        usage = entry.get("usage", {})
        result = {}
        for tier in ("primary", "secondary", "tertiary"):
            tier_data = usage.get(tier)
            if isinstance(tier_data, dict):
                result[tier] = tier_data
        result["plan"] = usage.get("loginMethod", "unknown")
        result["account"] = usage.get("accountEmail", "unknown")
        return result

    def provider_has_quota(self, provider: str) -> tuple[bool, str]:
        provider = provider.lower()
        if provider == "local":
            return True, "local (free)"

        stop_at = self.activity.get_stop_remaining_pct()
        time_label = "night" if self.activity.is_night() else "day"
        usage = self.get_codexbar_usage(provider)
        if not usage:
            print(f"⚠️ Could not fetch {provider} quota from codexbar — proceeding without guard")
            return True, f"{provider} unknown (codexbar unavailable)"

        primary = usage.get("primary") or {}
        secondary = usage.get("secondary") or {}
        daily_remaining = self.remaining_percent(primary)
        weekly_remaining = self.remaining_percent(secondary)

        warnings: list[str] = []
        if daily_remaining is not None and daily_remaining <= self.config.daily_warn_remaining_pct:
            warnings.append(
                f"daily quota low: {daily_remaining}% left "
                f"(warn at ≤{self.config.daily_warn_remaining_pct}%)"
            )
        if weekly_remaining is not None and weekly_remaining <= self.config.weekly_warn_remaining_pct:
            warnings.append(
                f"weekly quota low: {weekly_remaining}% left "
                f"(warn at ≤{self.config.weekly_warn_remaining_pct}%)"
            )
        if warnings:
            print(f"⚠️ {provider} quota warning: " + "; ".join(warnings))

        if daily_remaining is not None and daily_remaining <= stop_at:
            return False, (
                f"{provider} daily quota {daily_remaining}% left "
                f"(stop at ≤{stop_at}% {time_label})"
            )

        weekly_stop = self.config.weekly_stop_remaining_pct
        if weekly_stop > 0 and weekly_remaining is not None and weekly_remaining <= weekly_stop:
            return False, (
                f"{provider} weekly quota {weekly_remaining}% left "
                f"(stop at ≤{weekly_stop}%)"
            )

        parts = []
        if daily_remaining is not None:
            parts.append(f"daily {daily_remaining}% left")
        if weekly_remaining is not None:
            parts.append(f"weekly {weekly_remaining}% left")
        quota_summary = ", ".join(parts) if parts else "quota windows unavailable"
        warning_summary = f"; warning: {'; '.join(warnings)}" if warnings else ""
        weekly_stop_summary = f", weekly stop at ≤{weekly_stop}%" if weekly_stop > 0 else ""
        return True, (
            f"{provider} quota OK ({quota_summary}; daily stop at ≤{stop_at}% "
            f"{time_label}{weekly_stop_summary}{warning_summary})"
        )

    @staticmethod
    def remaining_percent(tier: dict) -> Optional[int]:
        used = tier.get("usedPercent")
        if used is None:
            return None
        try:
            return max(0, min(100, 100 - int(used)))
        except (TypeError, ValueError):
            return None

    @property
    def processed_commands_file(self):
        return self.config.state_dir / "clawqueue_processed_commands.json"

    def load_processed_commands(self) -> set[int]:
        try:
            data = json.loads(self.processed_commands_file.read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            return set()
        if not isinstance(data, list):
            return set()
        result: set[int] = set()
        for item in data:
            try:
                result.add(int(item))
            except (TypeError, ValueError):
                continue
        return result

    def save_processed_commands(self, processed: set[int]) -> None:
        try:
            self.processed_commands_file.write_text(
                json.dumps(sorted(processed)[-1000:]),
                encoding="utf-8",
            )
        except OSError as exc:
            print(f"⚠️ Could not save processed CQ commands: {exc}", file=sys.stderr)

    def process_slash_commands(self) -> None:
        processed = self.load_processed_commands()
        changed = False
        for issue in self.tracker.list_issues("all"):
            repo = issue.get("_repo", self.config.taskboard_repo)
            number = int(issue["number"])
            title = issue.get("title", "")
            labels = [
                label.get("name", "") if isinstance(label, dict) else str(label)
                for label in (issue.get("labels") or [])
            ]
            comments = self.tracker.issue_comments(repo, number)
            for index, comment in enumerate(comments):
                comment_id = comment.get("id")
                try:
                    command_id = int(comment_id)
                except (TypeError, ValueError):
                    continue
                if command_id in processed:
                    continue
                body = str(comment.get("body", ""))
                command = self.extract_cq_command(body)
                if not command:
                    continue
                if self.command_already_consumed(command, comments, index):
                    processed.add(command_id)
                    changed = True
                    continue
                self.apply_slash_command(command, repo, number, title, labels)
                processed.add(command_id)
                changed = True
        if changed:
            self.save_processed_commands(processed)

    @staticmethod
    def is_command_result_comment(body: str) -> bool:
        """Return true for both legacy and simplified CQ command ack comments."""
        stripped = body.lstrip()
        return stripped.startswith("### CQ command result:") or (
            stripped.startswith("### CQ ") and " command" in stripped.splitlines()[0]
        )

    @classmethod
    def command_already_acknowledged(cls, comments: list, command_index: int) -> bool:
        """Return true when a historical slash command already has a CQ response."""
        for comment in comments[command_index + 1 :]:
            body = str((comment or {}).get("body", ""))
            if cls.is_command_result_comment(body):
                return True
        return False

    @classmethod
    def command_already_consumed(cls, command: str, comments: list, command_index: int) -> bool:
        """Return true when GitHub history proves a command is no longer live.

        The processed-command state file is local runtime state and intentionally
        bounded. If it is deleted, moved to another machine, or pruned, CQ must
        not replay old `/cq retry` comments forever. GitHub comments are the
        durable history.

        A later CQ command-result comment means CQ already handled the command.
        For `/cq retry`, a later completion also means the retry already caused
        a worker run and should be marked processed instead of reopening done
        work again.
        """
        if cls.command_already_acknowledged(comments, command_index):
            return True
        if command != "retry":
            return False
        for comment in comments[command_index + 1 :]:
            body = str((comment or {}).get("body", ""))
            if cls.is_completion_comment(body):
                return True
        return False

    @staticmethod
    def extract_cq_command(body: str) -> Optional[str]:
        for line in body.splitlines():
            stripped = line.strip().lower()
            if stripped.startswith("/cq"):
                parts = stripped.split()
                return parts[1] if len(parts) > 1 else "diagnose"
        return None

    def queue_status_key(self, repo: str, number: int) -> str:
        cache = self.tracker.build_board_cache()
        entry = cache.get(self.tracker.cache_key(repo, number), {})
        project = self.config.projects.get(entry.get("project", ""))
        if project and "ready" in project.status_options:
            return "ready"
        return "todo"

    def apply_slash_command(self, command: str, repo: str, number: int, title: str, labels: list[str]) -> None:
        if command in {"diagnose", "status"}:
            state, details = self.diagnose_issue(repo, number, title, labels)
            self.tracker.add_comment(
                repo,
                number,
                self.command_comment_body(
                    status=state,
                    repo=repo,
                    issue=number,
                    title=title,
                    command="diagnose" if command == "diagnose" else "status",
                    details=details,
                ),
            )
            command_name = "/cq diagnose" if command == "diagnose" else "/cq status (alias)"
            self.log_decision("command", command_name, extra={"repo": repo, "issue": number})
            return

        if command == "pause":
            self.tracker.add_label(repo, number, "cq:paused")
            self.tracker.remove_assignee(repo, number)
            self.tracker.add_comment(
                repo,
                number,
                self.command_comment_body(
                    status="paused",
                    repo=repo,
                    issue=number,
                    title=title,
                    command="pause",
                    details=["Paused. Use `/cq retry` to resume."],
                ),
            )
            self.log_decision("command", "/cq pause", extra={"repo": repo, "issue": number})
            return

        if command == "retry":
            for label in ("cq:paused", "cq:failed", "cq:blocked"):
                self.tracker.remove_label(repo, number, label)
            self.tracker.remove_assignee(repo, number)
            self.tracker.reopen_issue(repo, number)
            if self.active_task_key() == self.attempt_count_key(repo, number):
                self.config.active_file.unlink(missing_ok=True)
            self.reset_attempt_count(repo, number)
            self.tracker.set_project_board_status(number, self.queue_status_key(repo, number), title, labels, repo=repo)
            self.tracker.add_comment(
                repo,
                number,
                self.command_comment_body(
                    status="queued",
                    repo=repo,
                    issue=number,
                    title=title,
                    command="retry",
                    details=["Queued for retry."],
                ),
            )
            self.log_decision("command", "/cq retry", extra={"repo": repo, "issue": number})
            return

        if command == "run":
            self.tracker.remove_label(repo, number, "cq:paused")
            self.tracker.ensure_issue_in_project(number, title, labels, repo=repo)
            self.tracker.set_project_board_status(number, self.queue_status_key(repo, number), title, labels, repo=repo)
            self.tracker.add_comment(
                repo,
                number,
                self.command_comment_body(
                    status="queued",
                    repo=repo,
                    issue=number,
                    title=title,
                    command="run",
                    details=["Queued."],
                ),
            )
            self.log_decision("command", "/cq run", extra={"repo": repo, "issue": number})
            return

        self.tracker.add_comment(
            repo,
            number,
            self.command_comment_body(
                status="unknown command",
                repo=repo,
                issue=number,
                title=title,
                command=command,
                details=["Unknown command. Supported: `/cq diagnose`, `/cq run`, `/cq retry`, `/cq pause`."],
            ),
        )
        self.log_decision("command", f"unknown /cq {command}", extra={"repo": repo, "issue": number})

    def command_comment_body(
        self,
        *,
        status: str,
        repo: str,
        issue: int,
        title: str,
        command: str | None = None,
        details: list[str] | None = None,
    ) -> str:
        command_label = (command or status).strip().lower().replace("_", "-")
        lines = [f"### CQ {command_label} command", ""]
        for detail in details or []:
            lines.append(f"- {detail}")
        return "\n".join(lines).rstrip()

    def diagnose_issue(self, repo: str, number: int, title: str, labels: list[str]) -> tuple[str, list[str]]:
        key = self.attempt_count_key(repo, number)
        active_key = self.active_task_key()
        attempts = self.get_attempt_count(repo, number)
        details = ["Diagnosis requested with `/cq diagnose`"]
        config_blockers: list[str] = []

        mode_label = self.runner.resolve_mode(labels)
        explicit_agent = self.extract_explicit_agent(labels)
        agent_candidates = self.config.resolve_agent_candidates(mode_label, explicit_agent)
        agent_name = agent_candidates[0] if agent_candidates else self.config.mode_to_agent.get(mode_label, "cto")
        provider = self.config.agent_provider.get(agent_name, "claude")
        deliverable_type = resolve_deliverable_type(labels, title)
        if explicit_agent:
            details.append(f"Routing: explicit agent override `{explicit_agent}` on role `{mode_label}`")
        elif len(agent_candidates) > 1:
            details.append(f"Routing: role `{mode_label}` → candidates `{', '.join(agent_candidates)}`")
        details.append(f"Routing: mode `{mode_label}` → agent `{agent_name}` ({provider})")
        details.append(f"Deliverable type: `{deliverable_type}` ({deliverable_label(deliverable_type)})")
        summary = self.tracker.get_issue_summary(repo, number) if hasattr(self.tracker, "get_issue_summary") else {}
        deps_ready, blocked_by_deps = self.dependencies_ready(repo, number, summary.get("body", "")) if summary else (True, [])
        if blocked_by_deps:
            details.append("Blocked: waiting for dependencies " + ", ".join(f"#{item}" for item in blocked_by_deps))
            config_blockers.append("dependencies are not completed yet")
        author_obj = summary.get("author") or {}
        author = author_obj.get("login", "") if isinstance(author_obj, dict) else ""
        allowlist_config = getattr(self.config, "change_author_allowlist", ())
        if deliverable_type == "change" and allowlist_config:
            allowed = ", ".join(f"`{item}`" for item in allowlist_config)
            if author and author.lower() in {item.lower() for item in allowlist_config}:
                details.append(f"Safety: cq:change author `{author}` is allowed ({allowed})")
            else:
                details.append(f"Safety blocker: cq:change is restricted to {allowed}; issue author is `{author or 'unknown'}`")
                config_blockers.append("cq:change author is not allowed by this company profile")
        if self.config.runner_backend == "openclaw":
            agents, agent_error = self.available_openclaw_agents()
            if agents and agent_name not in agents:
                available = ", ".join(f"`{item}`" for item in sorted(agents))
                config_blockers.append(
                    f"Config error: OpenClaw agent `{agent_name}` is not configured. Available agents: {available}"
                )
            elif agent_error:
                details.append(f"Agent check: could not verify OpenClaw agents: {agent_error}")

        cache = self.tracker.build_board_cache()
        board_entry = cache.get(self.tracker.cache_key(repo, number))
        board_status = board_entry.get("status") if board_entry else None
        if board_status:
            details.append(f"Board status: {board_status}")
        else:
            details.append("Board status: not found on a configured CQ project board")

        blocking_labels = {"cq:paused", "cq:failed", "cq:blocked"} & set(labels)
        if blocking_labels:
            details.append(
                f"Blocked: issue has {', '.join(f'`{label}`' for label in sorted(blocking_labels))}; use `/cq retry` when ready"
            )

        if config_blockers:
            details.extend(config_blockers)

        if active_key == key:
            state = "running"
            details.append("Active worker: this issue is the current CQ task")
        else:
            state = "diagnosed"
            if active_key:
                details.append(f"Active worker: another issue is running (`{active_key}`)")
            else:
                details.append("Active worker: none recorded")

        if attempts >= self.config.max_attempts_per_issue:
            details.append(
                f"Blocked: attempt limit reached ({attempts}/{self.config.max_attempts_per_issue}); use `/cq retry` to reset active/stuck state, or clear attempts manually if needed"
            )
        else:
            details.append(f"Attempts: {attempts}/{self.config.max_attempts_per_issue}")

        if self.config.lock_file.exists():
            try:
                lock_data = json.loads(self.config.lock_file.read_text())
            except (json.JSONDecodeError, OSError):
                lock_data = {}
            lock_pid = lock_data.get("pid")
            if self.pid_alive(lock_pid):
                details.append(f"Dispatcher lock: active pid {lock_pid}")
            else:
                details.append("Dispatcher lock: stale lock file present; next scheduler run should clean it")
        else:
            details.append("Dispatcher lock: none")

        if self.config.last_run_file.exists():
            try:
                last_run = float(self.config.last_run_file.read_text().strip())
                age_min = (time.time() - last_run) / 60
                if age_min < self.config.min_run_interval_min:
                    remaining = self.config.min_run_interval_min - age_min
                    details.append(f"Throttle: active for ~{remaining:.1f} more minutes")
                else:
                    details.append("Throttle: clear")
            except (OSError, ValueError):
                details.append("Throttle: unknown; last-run file unreadable")
        else:
            details.append("Throttle: clear")

        if config_blockers:
            state = "blocked"
            details.append("Next useful action: resolve the blocker above, then use `/cq retry`.")
        elif not board_status:
            details.append("Next useful command: `/cq run` to add/queue it")
        elif blocking_labels or attempts >= self.config.max_attempts_per_issue:
            details.append("Next useful command: `/cq retry` if this should run again")
        elif board_status == "Todo":
            details.append("Next action: scheduler should pick this when guards allow")
        elif board_status == "In Progress":
            details.append("Next action: wait for active worker, or `/cq retry` if it is stuck")
        elif board_status == "Review":
            details.append("Next action: reviewer agent should pick this when guards allow")
        else:
            details.append("Next action: no CQ action expected for this board status")

        return state, details

    def available_openclaw_agents(self) -> tuple[set[str], str]:
        out, rc = run_cmd(f"{self.config.openclaw_command} agents list", timeout=20)
        if rc != 0:
            return set(), out.strip()[:300] or f"exit {rc}"
        agents: set[str] = set()
        for line in out.splitlines():
            stripped = line.strip()
            if not stripped.startswith("- "):
                continue
            agent_id = stripped[2:].split(" ", 1)[0].strip()
            if agent_id:
                agents.add(agent_id)
        return agents, ""

    def sweep_stale_in_progress(self) -> None:
        self.cleanup_closed_issues()
        self.rescue_orphaned_tasks()
        self.rescue_review_without_completion()
        self.finalize_completed_reviews()

    def rescue_review_without_completion(self) -> None:
        """Move Review/In review items without CQ completion evidence back to Todo."""
        cache = self.tracker.build_board_cache()
        active_issue_key = self.active_task_key()

        for key, entry in list(cache.items()):
            if entry.get("status") not in ("Review", "In review"):
                continue
            repo, _, num_str = key.rpartition(":")
            try:
                number = int(num_str)
            except ValueError:
                continue
            if active_issue_key and self.attempt_count_key(repo, number) == active_issue_key:
                continue

            summary = self.tracker.get_issue_summary(repo, number)
            comments = summary.get("comments") or []
            if self.latest_completion_comment(comments):
                continue

            title = summary.get("title", "")
            labels = [label.get("name", "") for label in summary.get("labels", [])]
            details = [
                "CQ found this item in Review, but the issue has no CQ completion artifact (`<!-- clawqueue:done -->`).",
                "Moved back to Todo so the owner agent can produce a completion artifact before review.",
            ]
            print(f"↩️ Review without completion: {repo}#{number} → Todo")
            self.tracker.upsert_managed_comment(
                repo,
                number,
                progress_body(
                    status="queued",
                    repo=repo,
                    issue=number,
                    title=title,
                    details=details,
                ),
            )
            self.tracker.set_project_board_status(number, "todo", title, labels, repo=repo)

    def finalize_completed_reviews(self) -> None:
        """Move reviewed CQ tasks from Review/In review to Done.

        A reviewer can post a valid `needs_review: false` CQ result even after
        the active worker marker is gone. Without this sweep the issue remains
        queueable in Review/In review and CQ may repeatedly try to re-dispatch
        it, especially when quota guards prevent the duplicate review from
        starting.
        """
        cache = self.tracker.build_board_cache()
        active_issue_key = self.active_task_key()

        for key, entry in list(cache.items()):
            if entry.get("status") not in ("Review", "In review"):
                continue
            repo, _, num_str = key.rpartition(":")
            try:
                number = int(num_str)
            except ValueError:
                continue
            if active_issue_key and self.attempt_count_key(repo, number) == active_issue_key:
                continue

            summary = self.tracker.get_issue_summary(repo, number)
            labels = [label.get("name", "") for label in summary.get("labels", [])]
            if self.completed_status_key(repo, number, summary) != "done":
                continue

            title = summary.get("title", "")
            result = extract_result(self.latest_completion_comment(summary.get("comments") or [])) or {}
            details = [
                "Worker result: done",
                "Summary: CQ reconciled completed review result and moved the project item to Done.",
            ]
            files_changed = result.get("files_changed") or []
            if files_changed:
                details.append("Deliverables: " + ", ".join(str(item) for item in files_changed))
            print(f"✅ Completed review: {repo}#{number} → Done")
            self.tracker.upsert_managed_comment(
                repo,
                number,
                progress_body(
                    status="done",
                    repo=repo,
                    issue=number,
                    title=title,
                    details=details,
                ),
            )
            self.tracker.set_project_board_status(number, "done", title, labels, repo=repo)
            self.maybe_close_completed_issue(repo, number, "done", "done")

    def active_task_key(self) -> Optional[str]:
        if not self.config.active_file.exists():
            return None
        try:
            active_data = json.loads(self.config.active_file.read_text())
            active_issue = active_data.get("issue")
            active_repo = active_data.get("repo", self.config.taskboard_repo)
            if active_issue:
                return self.attempt_count_key(active_repo, active_issue)
        except (json.JSONDecodeError, OSError):
            return None
        return None

    def maybe_close_completed_issue(self, repo: str, number: int, status_key: str, result_status: str = "done") -> None:
        if not self.config.reviewer_auto_closes_issue:
            return
        # Review means waiting for human/operator acceptance. Do not close the
        # GitHub issue here: a later closed-issue cleanup pass treats closed
        # issues as Done, which skips the intended review/retry window.
        if result_status != "done" or status_key != "done":
            return
        if self.tracker.get_issue_state(repo, number) == "CLOSED":
            return
        if self.tracker.close_issue(repo, number):
            print(f"🔒 Closed completed issue: {repo}#{number}")

    def cleanup_closed_issues(self) -> None:
        cache = self.tracker.build_board_cache()
        active_issue_key = self.active_task_key()

        for key, entry in list(cache.items()):
            if entry.get("status") not in ("In Progress", "In progress"):
                continue
            repo, _, num_str = key.rpartition(":")
            try:
                number = int(num_str)
            except ValueError:
                continue
            if active_issue_key and self.attempt_count_key(repo, number) == active_issue_key:
                continue

            state = self.tracker.get_issue_state(repo, number)
            if not state:
                continue
            if state == "CLOSED":
                print(f"🧹 Stale In Progress: {repo}#{number} is CLOSED → Done")
                self.tracker.set_project_board_status(number, "done", "", [], repo=repo)

    def rescue_orphaned_tasks(self) -> None:
        cache = self.tracker.build_board_cache()
        active_issue_key = self.active_task_key()

        for key, entry in list(cache.items()):
            if entry.get("status") not in ("In Progress", "In progress"):
                continue
            repo, _, num_str = key.rpartition(":")
            try:
                number = int(num_str)
            except ValueError:
                continue
            if active_issue_key and self.attempt_count_key(repo, number) == active_issue_key:
                continue

            state = self.tracker.get_issue_state(repo, number)
            if not state or state == "CLOSED":
                continue

            summary = self.tracker.get_issue_summary(repo, number)
            labels = [label.get("name", "") for label in summary.get("labels", [])]
            status_key = self.completed_status_key(repo, number, summary)
            self.tracker.remove_assignee(repo, number)
            if status_key == "review":
                print(f"🔍 Stale In Progress: {repo}#{number} has completion result → Review")
                self.tracker.set_project_board_status(number, status_key, "", labels, repo=repo)
            else:
                print(f"🧹 Stale In Progress: {repo}#{number} has no active worker → {status_key.title()}")
                self.tracker.set_project_board_status(number, status_key, "", labels, repo=repo)

    def load_attempt_counts(self) -> dict:
        try:
            return json.loads(self.config.attempt_count_file.read_text())
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            return {}

    def save_attempt_counts(self, counts: dict) -> None:
        self.config.attempt_count_file.write_text(json.dumps(counts))

    @staticmethod
    def attempt_count_key(repo: str, number: int) -> str:
        return f"{repo}:{number}"

    def increment_attempt_count(self, repo: str, number: int) -> int:
        counts = self.load_attempt_counts()
        key = self.attempt_count_key(repo, number)
        counts[key] = counts.get(key, 0) + 1
        self.save_attempt_counts(counts)
        return counts[key]

    def get_attempt_count(self, repo: str, number: int) -> int:
        return self.load_attempt_counts().get(self.attempt_count_key(repo, number), 0)

    def reset_attempt_count(self, repo: str, number: int) -> None:
        counts = self.load_attempt_counts()
        counts.pop(self.attempt_count_key(repo, number), None)
        self.save_attempt_counts(counts)

    @staticmethod
    def pid_alive(pid: Optional[int]) -> bool:
        if not pid:
            return False
        try:
            os.kill(pid, 0)
            return True
        except (OSError, TypeError):
            return False

    def check_lock(self) -> bool:
        if not self.config.lock_file.exists():
            return False
        try:
            data = json.loads(self.config.lock_file.read_text())
        except (json.JSONDecodeError, OSError):
            self.config.lock_file.unlink(missing_ok=True)
            return False
        if self.pid_alive(data.get("pid")):
            return True
        self.config.lock_file.unlink(missing_ok=True)
        return False

    def reconcile_completed_active_task(self) -> bool:
        """Complete an active task that already posted CQ's done marker.

        This handles the common case where the agent finished and commented
        `<!-- clawqueue:done -->`, but the wrapper process or active marker
        outlived the useful work. The scheduler cron calls this on every tick;
        notification is best-effort and completion remains GitHub/board driven.
        """
        if not self.config.active_file.exists():
            return False
        try:
            data = json.loads(self.config.active_file.read_text())
        except (json.JSONDecodeError, OSError):
            return False

        issue = data.get("issue")
        repo = data.get("repo", self.config.taskboard_repo)
        pid = data.get("worker_pid")
        if not issue:
            return False

        summary = self.tracker.get_issue_summary(repo, issue)
        comments = summary.get("comments") or []
        if not comments:
            return False
        body = self.latest_completion_comment(comments)
        if not body:
            return False

        status_key = self.completed_status_key(repo, issue, summary)
        result = extract_result(body) or {}
        title = summary.get("title", "")
        labels = [label.get("name", "") for label in summary.get("labels", [])]
        result_status = result.get("status", "legacy-done-marker")
        details = [
            f"Worker result: {result_status}",
            f"Summary: {result.get('summary', '').strip()}" if result.get('summary') else "Summary: completion marker found",
        ]
        files_changed = result.get("files_changed") or []
        if files_changed:
            details.append("Deliverables: " + ", ".join(str(item) for item in files_changed))
        if result_status in {"failed", "blocked"}:
            self.tracker.add_label(repo, issue, "cq:paused")
            self.tracker.add_label(repo, issue, f"cq:{result_status}")
            details.append("Moved to Review and paused after failed/blocked result; use `/cq retry` when ready to run again.")
        print(f"🧹 Active task completed: {repo}#{issue} → {status_key.title()}")
        self.tracker.upsert_managed_comment(
            repo,
            issue,
            progress_body(
                status=str(result_status) if result_status in {"failed", "blocked"} else status_key,
                repo=repo,
                issue=issue,
                title=title,
                details=details,
            ),
        )
        self.tracker.set_project_board_status(issue, status_key, title, labels, repo=repo)
        self.tracker.remove_assignee(repo, issue)
        self.maybe_close_completed_issue(repo, issue, status_key, str(result_status))
        try:
            self.notifier.notify_completion(
                repo=repo,
                issue_number=issue,
                title=title,
                status=status_key,
                comments=comments,
            )
        except Exception as exc:
            print(f"⚠️ Completion notification error: {exc}")
        if self.pid_alive(pid):
            try:
                os.kill(pid, 15)
            except OSError:
                pass
        self.config.active_file.unlink(missing_ok=True)
        return True

    def worker_is_running(self) -> bool:
        if not self.config.active_file.exists():
            return False
        try:
            data = json.loads(self.config.active_file.read_text())
        except (json.JSONDecodeError, OSError):
            self.config.active_file.unlink(missing_ok=True)
            return False

        pid = data.get("worker_pid")
        issue = data.get("issue")
        repo = data.get("repo", self.config.taskboard_repo)
        if self.pid_alive(pid):
            return True
        if issue:
            state = self.tracker.get_issue_state(repo, issue)
            summary = self.tracker.get_issue_summary(repo, issue)
            status_key = (
                "done" if state == "CLOSED" else self.completed_status_key(repo, issue, summary)
            )
            title = summary.get("title", "")
            labels = [label.get("name", "") for label in summary.get("labels", [])]
            comments = summary.get("comments") or []
            body = self.latest_completion_comment(comments)
            result = extract_result(body) or {}
            result_status = result.get("status")
            details = ["Worker process exited; CQ reconciled issue state."]
            progress_status = status_key
            if result_status in {"failed", "blocked"}:
                self.tracker.add_label(repo, issue, "cq:paused")
                self.tracker.add_label(repo, issue, f"cq:{result_status}")
                progress_status = str(result_status)
                details.append("Moved to Review and paused after failed/blocked result; use `/cq retry` when ready to run again.")
            self.tracker.upsert_managed_comment(
                repo,
                issue,
                progress_body(
                    status=progress_status,
                    repo=repo,
                    issue=issue,
                    title=title,
                    details=details,
                ),
            )
            self.tracker.set_project_board_status(issue, status_key, title, labels, repo=repo)
            self.tracker.remove_assignee(repo, issue)
            if status_key in {"done", "review"}:
                try:
                    self.notifier.notify_completion(
                        repo=repo,
                        issue_number=issue,
                        title=title,
                        status=status_key,
                        comments=summary.get("comments") or [],
                    )
                except Exception as exc:
                    print(f"⚠️ Completion notification error: {exc}")
        self.config.active_file.unlink(missing_ok=True)
        return False

    def acquire_lock(self, repo: str, issue_number: int) -> None:
        self.config.lock_file.write_text(
            json.dumps(
                {
                    "pid": os.getpid(),
                    "repo": repo,
                    "issue": issue_number,
                    "started": datetime.now(timezone.utc).isoformat(),
                }
            )
        )

    def register_worker(self, issue_number: int, worker_pid: int, repo: str) -> None:
        self.config.active_file.write_text(
            json.dumps(
                {
                    "issue": issue_number,
                    "worker_pid": worker_pid,
                    "repo": repo,
                    "started": datetime.now(timezone.utc).isoformat(),
                }
            )
        )

    def release_lock(self) -> None:
        self.config.lock_file.unlink(missing_ok=True)

    def check_throttle(self) -> bool:
        if not self.config.last_run_file.exists():
            return False
        try:
            timestamp = float(self.config.last_run_file.read_text().strip())
        except (OSError, ValueError):
            return False
        return (time.time() - timestamp) / 60 < self.config.min_run_interval_min

    def record_run(self) -> None:
        try:
            self.config.last_run_file.write_text(str(time.time()))
        except OSError:
            pass

    def trim_decision_log(self) -> None:
        path = self.config.decision_log_file
        if not path.exists():
            return
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.config.decision_log_retention_days)
        kept: list[str] = []
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    ts = datetime.fromisoformat(json.loads(line).get("timestamp", ""))
                    if ts >= cutoff:
                        kept.append(line)
                except (json.JSONDecodeError, ValueError):
                    kept.append(line)  # keep malformed lines rather than silently drop
        except OSError:
            return
        try:
            path.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")
        except OSError as exc:
            print(f"⚠️ Could not trim decision log: {exc}", file=sys.stderr)

    def log_decision(
        self,
        decision: str,
        reason: str,
        task: Optional[Task] = None,
        extra: Optional[dict] = None,
    ) -> None:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "decision": decision,
            "reason": reason,
        }
        if task:
            entry.update(
                {
                    "repo": task.repo,
                    "issue": task.number,
                    "title": task.title,
                    "mode_label": task.mode_label,
                    "agent": task.agent_name,
                }
            )
        if extra:
            entry.update(extra)

        try:
            self.config.decision_log_file.parent.mkdir(parents=True, exist_ok=True)
            with self.config.decision_log_file.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(entry, sort_keys=True) + "\n")
        except OSError as exc:
            print(f"⚠️ Could not write decision log: {exc}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run one ClawQueue scheduler tick.")
    parser.add_argument("--profile", help="profile name under profiles/ to load")
    args = parser.parse_args(argv)
    try:
        config = load_config(profile=args.profile)
    except ConfigError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 2
    dispatcher = ClawQueueDispatcher(config)
    try:
        return dispatcher.main()
    except Exception as exc:
        print(f"❌ Unexpected error: {exc}", file=sys.stderr)
        dispatcher.log_decision("error", f"unexpected error: {exc}")
        dispatcher.release_lock()
        return 1
