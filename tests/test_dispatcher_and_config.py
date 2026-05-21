from __future__ import annotations

import os
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

from clawqueue.config import load_config
from clawqueue.dispatcher import ClawQueueDispatcher
from clawqueue.runner import COMPLETION_SENTINEL


@contextmanager
def patched_env(values: dict[str, str]):
    old_values = {key: os.environ.get(key) for key in values}
    os.environ.update(values)
    try:
        yield
    finally:
        for key, old_value in old_values.items():
            if old_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old_value


class DispatcherCompletionTests(unittest.TestCase):
    def test_completion_requires_done_prefix_or_sentinel(self) -> None:
        self.assertTrue(ClawQueueDispatcher.is_completion_comment("Done - implemented"))
        self.assertTrue(ClawQueueDispatcher.is_completion_comment(COMPLETION_SENTINEL))
        self.assertFalse(ClawQueueDispatcher.is_completion_comment("I am not done yet"))
        self.assertFalse(ClawQueueDispatcher.is_completion_comment("server done crashed"))

    def test_latest_completion_comment_ignores_later_housekeeping(self) -> None:
        done = f"<!-- clawqueue:result -->\n{{}}\n{COMPLETION_SENTINEL}"
        comments = [
            {"body": "running"},
            {"body": done},
            {"body": "housekeeping link update"},
        ]
        self.assertEqual(ClawQueueDispatcher.latest_completion_comment(comments), done)

    def test_latest_completion_comment_after_ignores_old_completion(self) -> None:
        old_done = f"<!-- clawqueue:result -->\n{{\"status\":\"done\"}}\n{COMPLETION_SENTINEL}"
        new_done = f"<!-- clawqueue:result -->\n{{\"status\":\"done\",\"summary\":\"new\"}}\n{COMPLETION_SENTINEL}"
        comments = [
            {"body": old_done, "createdAt": "2026-05-21T12:00:00Z"},
            {"body": "/cq retry", "createdAt": "2026-05-21T13:00:00Z"},
            {"body": "worker note", "createdAt": "2026-05-21T13:05:00Z"},
        ]

        self.assertEqual(
            ClawQueueDispatcher.latest_completion_comment_after(comments, "2026-05-21T13:01:00+00:00"),
            "",
        )

        comments.append({"body": new_done, "createdAt": "2026-05-21T13:10:00Z"})
        self.assertEqual(
            ClawQueueDispatcher.latest_completion_comment_after(comments, "2026-05-21T13:01:00+00:00"),
            new_done,
        )

    def test_unacknowledged_retry_after_completion_makes_issue_queueable_again(self) -> None:
        done = f"<!-- clawqueue:result -->\n```json\n{{\"status\":\"done\",\"needs_review\":true}}\n```\n{COMPLETION_SENTINEL}"
        comments = [
            {"body": done},
            {"body": "/cq retry\nReprocess this."},
        ]
        dispatcher = ClawQueueDispatcher.__new__(ClawQueueDispatcher)
        dispatcher.tracker = SimpleNamespace(
            build_board_cache=lambda: {"owner/repo:7": {"project": "P"}},
            cache_key=lambda repo, number: f"{repo}:{number}",
        )
        dispatcher.config = SimpleNamespace(projects={"P": SimpleNamespace(status_options={"review": "review-id"})})

        self.assertTrue(ClawQueueDispatcher.has_retry_after_latest_completion(comments))
        self.assertEqual(dispatcher.completed_status_key("owner/repo", 7, {"labels": [], "comments": comments}), "todo")

    def test_acknowledged_retry_after_completion_does_not_stay_queueable(self) -> None:
        done = f"<!-- clawqueue:result -->\n```json\n{{\"status\":\"done\",\"needs_review\":true}}\n```\n{COMPLETION_SENTINEL}"
        comments = [
            {"body": done},
            {"body": "/cq retry\nReprocess this."},
            {"body": "### CQ command result: queued"},
        ]
        dispatcher = ClawQueueDispatcher.__new__(ClawQueueDispatcher)
        dispatcher.tracker = SimpleNamespace(
            build_board_cache=lambda: {"owner/repo:7": {"project": "P"}},
            cache_key=lambda repo, number: f"{repo}:{number}",
        )
        dispatcher.config = SimpleNamespace(projects={"P": SimpleNamespace(status_options={"review": "review-id"})})

        self.assertFalse(ClawQueueDispatcher.has_retry_after_latest_completion(comments))
        self.assertEqual(dispatcher.completed_status_key("owner/repo", 7, {"labels": [], "comments": comments}), "review")

    def test_change_completion_routes_to_review_when_review_column_exists(self) -> None:
        done = f"<!-- clawqueue:result -->\n```json\n{{\"status\":\"done\",\"needs_review\":true}}\n```\n{COMPLETION_SENTINEL}"
        dispatcher = ClawQueueDispatcher.__new__(ClawQueueDispatcher)
        dispatcher.tracker = SimpleNamespace(
            build_board_cache=lambda: {"owner/repo:8": {"project": "P", "status": "In Progress"}},
            cache_key=lambda repo, number: f"{repo}:{number}",
        )
        dispatcher.config = SimpleNamespace(projects={"P": SimpleNamespace(status_options={"review": "review-id"})})

        self.assertEqual(
            dispatcher.completed_status_key(
                "owner/repo",
                8,
                {"labels": [{"name": "cq:change"}], "comments": [{"body": done}]},
            ),
            "review",
        )

    def test_review_completion_with_no_followup_review_routes_to_done(self) -> None:
        done = f"<!-- clawqueue:result -->\n```json\n{{\"status\":\"done\",\"needs_review\":false}}\n```\n{COMPLETION_SENTINEL}"
        dispatcher = ClawQueueDispatcher.__new__(ClawQueueDispatcher)
        dispatcher.tracker = SimpleNamespace(
            build_board_cache=lambda: {"owner/repo:9": {"project": "P", "status": "Review"}},
            cache_key=lambda repo, number: f"{repo}:{number}",
        )
        dispatcher.config = SimpleNamespace(projects={"P": SimpleNamespace(status_options={"review": "review-id"})})

        self.assertEqual(
            dispatcher.completed_status_key(
                "owner/repo",
                9,
                {"labels": [{"name": "cq:change"}], "comments": [{"body": done}]},
            ),
            "done",
        )

    def test_dependency_numbers_are_parsed_from_issue_body(self) -> None:
        body = """
        ## Dependencies
        - depends on Issue #4
        - depends on #5
        - can run in parallel with Issue #2
        """
        self.assertEqual(ClawQueueDispatcher.dependency_issue_numbers(body), {4, 5})

    def test_dependencies_block_when_dependency_was_retried_after_completion(self) -> None:
        done = f"<!-- clawqueue:result -->\n```json\n{{\"status\":\"done\"}}\n```\n{COMPLETION_SENTINEL}"
        summaries = {
            4: {"comments": [{"body": done}]},
            5: {"comments": [{"body": done}, {"body": "/cq retry"}]},
        }
        dispatcher = ClawQueueDispatcher.__new__(ClawQueueDispatcher)
        dispatcher.tracker = SimpleNamespace(
            build_board_cache=lambda: {},
            cache_key=lambda repo, number: f"{repo}:{number}",
            get_issue_summary=lambda repo, number: summaries[number],
        )

        ready, blocked_by = dispatcher.dependencies_ready("owner/repo", 6, "depends on Issue #4\ndepends on Issue #5")

        self.assertFalse(ready)
        self.assertEqual(blocked_by, [5])

    def test_retry_does_not_clear_live_active_worker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            active_file = Path(tmp) / "active.json"
            active_file.write_text('{"issue": 7, "repo": "owner/repo", "worker_pid": %d}' % os.getpid())
            calls: list[str] = []
            comments: list[str] = []
            dispatcher = ClawQueueDispatcher.__new__(ClawQueueDispatcher)
            dispatcher.config = SimpleNamespace(
                active_file=active_file,
                taskboard_repo="owner/repo",
                attempt_count_file=Path(tmp) / "attempts.json",
                decision_log_file=Path(tmp) / "decisions.jsonl",
                decision_log_retention_days=7,
            )
            dispatcher.tracker = SimpleNamespace(
                add_comment=lambda repo, number, body: comments.append(body),
                remove_label=lambda repo, number, label: calls.append(f"remove_label:{label}"),
                remove_assignee=lambda repo, number: calls.append("remove_assignee"),
                reopen_issue=lambda repo, number: calls.append("reopen_issue"),
                set_project_board_status=lambda number, status, title, labels, repo: calls.append(f"status:{status}"),
                build_board_cache=lambda: {"owner/repo:7": {"project": "P"}},
                cache_key=lambda repo, number: f"{repo}:{number}",
            )

            dispatcher.apply_slash_command("retry", "owner/repo", 7, "Task", [], command_id=123)

            self.assertEqual(calls, [])
            self.assertTrue(active_file.exists())
            self.assertIn("CQ command result: running", comments[0])
            self.assertIn("already In Progress", comments[0])
            self.assertIn("<!-- clawqueue:command:123 -->", comments[0])

    def test_retry_does_not_move_in_progress_issue_even_without_active_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            active_file = Path(tmp) / "active.json"
            calls: list[str] = []
            comments: list[str] = []
            dispatcher = ClawQueueDispatcher.__new__(ClawQueueDispatcher)
            dispatcher.config = SimpleNamespace(
                active_file=active_file,
                taskboard_repo="owner/repo",
                attempt_count_file=Path(tmp) / "attempts.json",
                decision_log_file=Path(tmp) / "decisions.jsonl",
                decision_log_retention_days=7,
            )
            dispatcher.tracker = SimpleNamespace(
                add_comment=lambda repo, number, body: comments.append(body),
                remove_label=lambda repo, number, label: calls.append(f"remove_label:{label}"),
                remove_assignee=lambda repo, number: calls.append("remove_assignee"),
                reopen_issue=lambda repo, number: calls.append("reopen_issue"),
                set_project_board_status=lambda number, status, title, labels, repo: calls.append(f"status:{status}"),
                build_board_cache=lambda: {"owner/repo:7": {"status": "In Progress", "project": "P"}},
                cache_key=lambda repo, number: f"{repo}:{number}",
            )

            dispatcher.apply_slash_command("retry", "owner/repo", 7, "Task", ["cq:blocked"], command_id=123)

            self.assertEqual(calls, [])
            self.assertFalse(active_file.exists())
            self.assertIn("CQ command result: running", comments[0])
            self.assertIn("labels, assignment, attempt count", comments[0])

    def test_process_slash_commands_skips_already_acknowledged_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            applied: list[str] = []
            dispatcher = ClawQueueDispatcher.__new__(ClawQueueDispatcher)
            dispatcher.config = SimpleNamespace(
                state_dir=Path(tmp),
                command_ledger_file=Path(tmp) / "commands.json",
                taskboard_repo="owner/repo",
            )
            dispatcher.tracker = SimpleNamespace(
                list_issues=lambda state: [{"number": 7, "title": "Task", "labels": [], "_repo": "owner/repo"}],
                issue_comments=lambda repo, number: [
                    {"id": 123, "body": "/cq retry"},
                    {"id": 124, "body": "<!-- clawqueue:command:123 -->\n### CQ command result: queued"},
                ],
            )
            dispatcher.apply_slash_command = lambda command, repo, number, title, labels, command_id=None: applied.append(command)  # type: ignore[method-assign]

            self.assertTrue(dispatcher.process_slash_commands())

            self.assertEqual(applied, [])
            self.assertEqual(dispatcher.load_processed_commands(), {123})

    def test_dead_worker_ignores_completion_from_before_worker_start(self) -> None:
        done = f"<!-- clawqueue:result -->\n```json\n{{\"status\":\"done\"}}\n```\n{COMPLETION_SENTINEL}"
        with tempfile.TemporaryDirectory() as tmp:
            active_file = Path(tmp) / "active.json"
            active_file.write_text(
                '{"issue": 7, "repo": "owner/repo", "worker_pid": 999999, '
                '"started": "2026-05-21T13:01:00+00:00"}'
            )
            status_updates: list[str] = []
            comments: list[str] = []
            dispatcher = ClawQueueDispatcher.__new__(ClawQueueDispatcher)
            dispatcher.config = SimpleNamespace(
                active_file=active_file,
                taskboard_repo="owner/repo",
            )
            dispatcher.tracker = SimpleNamespace(
                get_issue_state=lambda repo, number: "OPEN",
                get_issue_summary=lambda repo, number: {
                    "title": "Task",
                    "labels": [],
                    "comments": [{"body": done, "createdAt": "2026-05-21T13:00:00Z"}],
                },
                upsert_managed_comment=lambda repo, number, body: comments.append(body),
                set_project_board_status=lambda number, status, title, labels, repo: status_updates.append(status),
                remove_assignee=lambda repo, number: None,
            )
            dispatcher.pid_alive = lambda pid: False  # type: ignore[method-assign]
            dispatcher.queue_status_key = lambda repo, number: "todo"  # type: ignore[method-assign]
            dispatcher.completed_status_key = lambda repo, number, summary: self.fail("old completion should not be reused")  # type: ignore[method-assign]

            self.assertFalse(dispatcher.worker_is_running())

            self.assertEqual(status_updates, ["todo"])
            self.assertFalse(active_file.exists())
            self.assertIn("No completion marker was posted after this worker started", comments[0])

    def test_dead_worker_uses_completion_after_worker_start(self) -> None:
        done = f"<!-- clawqueue:result -->\n```json\n{{\"status\":\"done\"}}\n```\n{COMPLETION_SENTINEL}"
        with tempfile.TemporaryDirectory() as tmp:
            active_file = Path(tmp) / "active.json"
            active_file.write_text(
                '{"issue": 7, "repo": "owner/repo", "worker_pid": 999999, '
                '"started": "2026-05-21T13:00:00+00:00"}'
            )
            status_updates: list[str] = []
            dispatcher = ClawQueueDispatcher.__new__(ClawQueueDispatcher)
            dispatcher.config = SimpleNamespace(
                active_file=active_file,
                taskboard_repo="owner/repo",
            )
            dispatcher.tracker = SimpleNamespace(
                get_issue_state=lambda repo, number: "OPEN",
                get_issue_summary=lambda repo, number: {
                    "title": "Task",
                    "labels": [],
                    "comments": [{"body": done, "createdAt": "2026-05-21T13:01:00Z"}],
                },
                upsert_managed_comment=lambda repo, number, body: None,
                set_project_board_status=lambda number, status, title, labels, repo: status_updates.append(status),
                remove_assignee=lambda repo, number: None,
            )
            dispatcher.pid_alive = lambda pid: False  # type: ignore[method-assign]
            dispatcher.completed_status_key = lambda repo, number, summary: "review"  # type: ignore[method-assign]

            self.assertFalse(dispatcher.worker_is_running())

            self.assertEqual(status_updates, ["review"])
            self.assertFalse(active_file.exists())

    def test_processed_command_ledger_reads_legacy_state_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp) / "profile"
            shared_root = Path(tmp)
            state_dir.mkdir()
            (state_dir / "clawqueue_processed_commands.json").write_text("[111]")
            (shared_root / "clawqueue_processed_commands.json").write_text("[222]")
            dispatcher = ClawQueueDispatcher.__new__(ClawQueueDispatcher)
            dispatcher.config = SimpleNamespace(
                state_dir=state_dir,
                shared_state_root=shared_root,
                command_ledger_file=shared_root / "commands" / "owner-repo.json",
            )

            self.assertEqual(dispatcher.load_processed_commands(), {111, 222})


class FakeTracker:
    def __init__(self) -> None:
        self.status_updates: list[tuple[int, str, str, list[str], str]] = []
        self.comments: list[tuple[str, int, str]] = []
        self.closed: list[tuple[str, int, str]] = []

    def build_board_cache(self) -> dict:
        return {
            "ExampleOrg/ExampleRepo:1": {"status": "In review"},
            "ExampleOrg/ExampleRepo:2": {"status": "Todo"},
        }

    def get_issue_summary(self, repo: str, number: int) -> dict:
        return {
            "title": f"Issue {number}",
            "labels": [{"name": "cto"}],
        }

    def upsert_managed_comment(self, repo: str, number: int, body: str) -> None:
        self.comments.append((repo, number, body))

    def set_project_board_status(self, number: int, status_key: str, title: str, labels: list[str], *, repo: str) -> None:
        self.status_updates.append((number, status_key, title, labels, repo))

    def get_issue_state(self, repo: str, number: int) -> str:
        return "OPEN"

    def close_issue(self, repo: str, number: int, reason: str = "completed") -> bool:
        self.closed.append((repo, number, reason))
        return True


class DispatcherReviewSweepTests(unittest.TestCase):
    def test_maybe_close_completed_issue_leaves_review_open(self) -> None:
        dispatcher = ClawQueueDispatcher.__new__(ClawQueueDispatcher)
        dispatcher.config = SimpleNamespace(reviewer_auto_closes_issue=True)
        dispatcher.tracker = FakeTracker()

        dispatcher.maybe_close_completed_issue("ExampleOrg/ExampleRepo", 1, "review", "done")

        self.assertEqual(dispatcher.tracker.closed, [])

    def test_maybe_close_completed_issue_closes_done(self) -> None:
        dispatcher = ClawQueueDispatcher.__new__(ClawQueueDispatcher)
        dispatcher.config = SimpleNamespace(reviewer_auto_closes_issue=True)
        dispatcher.tracker = FakeTracker()

        dispatcher.maybe_close_completed_issue("ExampleOrg/ExampleRepo", 1, "done", "done")

        self.assertEqual(dispatcher.tracker.closed, [("ExampleOrg/ExampleRepo", 1, "completed")])

    def test_finalize_completed_reviews_leaves_review_for_human_done(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dispatcher = ClawQueueDispatcher.__new__(ClawQueueDispatcher)
            dispatcher.config = SimpleNamespace(active_file=Path(tmp) / "active.json", reviewer_auto_closes_issue=True, taskboard_repo="ExampleOrg/ExampleRepo")
            dispatcher.tracker = FakeTracker()
            dispatcher.completed_status_key = lambda repo, number, summary: "review"  # type: ignore[method-assign]

            dispatcher.finalize_completed_reviews()

        self.assertEqual(dispatcher.tracker.status_updates, [])
        self.assertEqual(dispatcher.tracker.comments, [])
        self.assertEqual(dispatcher.tracker.closed, [])


class ConfigTests(unittest.TestCase):
    def test_default_policy_maps_reviewer_role(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            from clawqueue.config import DEFAULT_POLICY_FILE

            with patched_env(
                {
                    "CLAWQUEUE_POLICY_FILE": str(DEFAULT_POLICY_FILE),
                    "CLAWQUEUE_PRIVATE_CONFIG_FILE": str(Path(tmp) / "missing.json"),
                    "CLAWQUEUE_STATE_DIR": str(Path(tmp) / "state"),
                }
            ):
                config = load_config()

        self.assertEqual(config.resolve_agent_candidates("reviewer"), ("reviewer",))

    def test_provider_names_and_new_policy_keys_are_normalized(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            policy = Path(tmp) / "policy.md"
            state_dir = Path(tmp) / "state"
            policy.write_text(
                """---
{
  "runtime": {
    "max_attempts_per_issue": 7
  },
  "routing": {
    "agent_provider": {
      "cto": "CODEX",
      "researcher": "Claude"
    }
  },
  "github": {
    "reviewer_auto_closes_issue": false
  },
  "projects": {}
}
---
""",
                encoding="utf-8",
            )

            with patched_env(
                {
                    "CLAWQUEUE_POLICY_FILE": str(policy),
                    "CLAWQUEUE_PRIVATE_CONFIG_FILE": str(Path(tmp) / "missing.json"),
                    "CLAWQUEUE_STATE_DIR": str(state_dir),
                }
            ):
                config = load_config()

        self.assertEqual(config.max_attempts_per_issue, 7)
        self.assertFalse(config.reviewer_auto_closes_issue)
        self.assertEqual(config.agent_provider["cto"], "codex")
        self.assertEqual(config.agent_provider["researcher"], "claude")
        self.assertEqual(config.shared_state_root, state_dir.parent)
        self.assertEqual(config.command_ledger_file, state_dir.parent / "commands" / "example-org-clawqueue.json")
        self.assertEqual(config.active_file, state_dir.parent / "active" / "example-org-clawqueue.json")

    def test_profile_state_dirs_share_repo_scoped_runtime_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            policy = Path(tmp) / "policy.md"
            state_dir = Path(tmp) / "state" / "profile-a"
            policy.write_text(
                """---
{
  "repositories": {"primary": "Owner/Repo"},
  "projects": {}
}
---
""",
                encoding="utf-8",
            )

            with patched_env(
                {
                    "CLAWQUEUE_POLICY_FILE": str(policy),
                    "CLAWQUEUE_PRIVATE_CONFIG_FILE": str(Path(tmp) / "missing.json"),
                    "CLAWQUEUE_STATE_DIR": str(state_dir),
                }
            ):
                config = load_config()

        self.assertEqual(config.shared_state_root, state_dir.parent)
        self.assertEqual(config.lock_file, state_dir.parent / "locks" / "Owner-Repo.lock")
        self.assertEqual(config.command_ledger_file, state_dir.parent / "commands" / "Owner-Repo.json")


class QuotaConfigTests(unittest.TestCase):
    def test_quota_warning_thresholds_are_configurable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            policy = Path(tmp) / "policy.md"
            state_dir = Path(tmp) / "state"
            policy.write_text(
                """---
{
  "quota": {
    "daily_warn_remaining_pct": 12,
    "weekly_warn_remaining_pct": 25,
    "weekly_stop_remaining_pct": 7,
    "daily_stop_remaining_pct": 4
  },
  "projects": {}
}
---
""",
                encoding="utf-8",
            )

            with patched_env(
                {
                    "CLAWQUEUE_POLICY_FILE": str(policy),
                    "CLAWQUEUE_PRIVATE_CONFIG_FILE": str(Path(tmp) / "missing.json"),
                    "CLAWQUEUE_STATE_DIR": str(state_dir),
                }
            ):
                config = load_config()

        self.assertEqual(config.daily_warn_remaining_pct, 12)
        self.assertEqual(config.weekly_warn_remaining_pct, 25)
        self.assertEqual(config.weekly_stop_remaining_pct, 7)
        self.assertEqual(config.day_stop_remaining_pct, 4)


class FakeActivity:
    def get_stop_remaining_pct(self) -> int:
        return 5

    def is_night(self) -> bool:
        return False


class QuotaDecisionTests(unittest.TestCase):
    def dispatcher_with_usage(self, usage: dict) -> ClawQueueDispatcher:
        with tempfile.TemporaryDirectory() as tmp:
            policy = Path(tmp) / "policy.md"
            policy.write_text('''---
{
  "projects": {}
}
---
''', encoding="utf-8")
            with patched_env(
                {
                    "CLAWQUEUE_POLICY_FILE": str(policy),
                    "CLAWQUEUE_PRIVATE_CONFIG_FILE": str(Path(tmp) / "missing.json"),
                    "CLAWQUEUE_STATE_DIR": str(Path(tmp) / "state"),
                }
            ):
                config = load_config()
        dispatcher = ClawQueueDispatcher.__new__(ClawQueueDispatcher)
        dispatcher.config = config
        dispatcher.activity = FakeActivity()
        dispatcher.get_codexbar_usage = lambda provider: usage  # type: ignore[method-assign]
        return dispatcher

    def test_provider_warns_on_daily_and_weekly_thresholds_without_stopping(self) -> None:
        dispatcher = self.dispatcher_with_usage(
            {
                "primary": {"usedPercent": 91},
                "secondary": {"usedPercent": 81},
            }
        )

        ok, reason = dispatcher.provider_has_quota("codex")

        self.assertTrue(ok)
        self.assertIn("daily 9% left", reason)
        self.assertIn("weekly 19% left", reason)
        self.assertIn("warning:", reason)

    def test_provider_stops_on_weekly_threshold_when_enabled(self) -> None:
        with patched_env({"CLAWQUEUE_WEEKLY_STOP_REMAINING_PCT": "20"}):
            dispatcher = self.dispatcher_with_usage(
                {
                    "primary": {"usedPercent": 50},
                    "secondary": {"usedPercent": 85},
                }
            )

            ok, reason = dispatcher.provider_has_quota("codex")

        self.assertFalse(ok)
        self.assertIn("weekly quota 15% left", reason)

class RunnerPathTests(unittest.TestCase):
    def test_artifact_and_worker_log_paths_are_namespaced_by_board_and_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            policy = Path(tmp) / "policy.md"
            state_dir = Path(tmp) / "state"
            policy.write_text(
                """---
{
  "projects": {}
}
---
""",
                encoding="utf-8",
            )
            with patched_env(
                {
                    "CLAWQUEUE_POLICY_FILE": str(policy),
                    "CLAWQUEUE_PRIVATE_CONFIG_FILE": str(Path(tmp) / "missing.json"),
                    "CLAWQUEUE_STATE_DIR": str(state_dir),
                }
            ):
                config = load_config()

        from clawqueue.runner import AgentRunner
        from clawqueue.tracker import Task

        runner = AgentRunner(config, tracker=None)  # type: ignore[arg-type]
        task = Task(
            number=1,
            title="Task",
            body="",
            labels=["dev"],
            mode_label="dev",
            agent_name="manobot-cto",
            priority=0,
            repo="ExampleOrg/ExampleRepo",
            project_name="A2G",
        )

        self.assertEqual(
            runner.task_artifact_prefix(task),
            ".clawqueue/boards/A2G/0001-<slug>",
        )
        self.assertEqual(
            runner.worker_log_path(task),
            state_dir / "worker-logs" / "ExampleOrg-ExampleRepo" / "issue-0001.log",
        )
        prompt = runner.build_task_prompt(task)
        self.assertIn(
            ".clawqueue/boards/A2G/0001-<slug>.md",
            prompt,
        )
        self.assertIn("Artifact destination: write deliverables under `.clawqueue/boards`", prompt)


if __name__ == "__main__":
    unittest.main()
