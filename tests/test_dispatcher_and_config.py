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

    def test_retry_after_completion_makes_issue_queueable_again(self) -> None:
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

        self.assertTrue(ClawQueueDispatcher.has_retry_after_latest_completion(comments))
        self.assertEqual(dispatcher.completed_status_key("owner/repo", 7, {"labels": [], "comments": comments}), "todo")

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
    def test_finalize_completed_reviews_leaves_review_for_human_done(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dispatcher = ClawQueueDispatcher.__new__(ClawQueueDispatcher)
            dispatcher.config = SimpleNamespace(active_file=Path(tmp) / "active.json", reviewer_auto_closes_issue=True)
            dispatcher.tracker = FakeTracker()
            dispatcher.completed_status_key = lambda repo, number, summary: "review"  # type: ignore[method-assign]

            dispatcher.finalize_completed_reviews()

        self.assertEqual(dispatcher.tracker.status_updates, [])
        self.assertEqual(dispatcher.tracker.comments, [])
        self.assertEqual(dispatcher.tracker.closed, [])


class ConfigTests(unittest.TestCase):
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
