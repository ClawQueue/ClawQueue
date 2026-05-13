from __future__ import annotations

import unittest

from clawqueue.dispatcher import ClawQueueDispatcher
from clawqueue.progress import RESULT_MARKER, extract_result, progress_body, result_contract_text


class ProgressTests(unittest.TestCase):
    def test_progress_body_has_managed_marker_and_commands(self) -> None:
        body = progress_body(status="running", repo="owner/repo", issue=7, title="Task", details=["Agent: cto"])
        self.assertIn("<!-- clawqueue:progress -->", body)
        self.assertIn("/cq diagnose", body)
        self.assertIn("Agent: cto", body)

    def test_extract_result_contract(self) -> None:
        body = RESULT_MARKER + '''
```json
{"status":"done","summary":"ok","files_changed":["README.md"],"needs_review":true}
```
<!-- clawqueue:done -->
'''
        result = extract_result(body)
        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "done")
        self.assertEqual(result["summary"], "ok")
        self.assertTrue(result["needs_review"])

    def test_result_contract_text_mentions_clickable_deliverable_link(self) -> None:
        text = result_contract_text(4, "ExampleOrg/ExampleRepo")
        self.assertIn("Deliverable: [friendly label]", text)
        self.assertIn("<!-- clawqueue:result -->", text)
        self.assertIn("<!-- clawqueue:done -->", text)

    def test_extract_cq_command_requires_line_start(self) -> None:
        self.assertEqual(ClawQueueDispatcher.extract_cq_command("/cq retry"), "retry")
        self.assertEqual(ClawQueueDispatcher.extract_cq_command("  /cq"), "diagnose")
        self.assertIsNone(ClawQueueDispatcher.extract_cq_command("Please run `/cq retry` maybe"))

    def test_command_comment_body_is_append_only_not_managed_progress(self) -> None:
        dispatcher = ClawQueueDispatcher.__new__(ClawQueueDispatcher)
        body = dispatcher.command_comment_body(
            status="diagnosed",
            repo="owner/repo",
            issue=7,
            title="Task",
            command="diagnose",
            details=["Diagnosis requested with `/cq diagnose`"],
        )

        self.assertIn("CQ diagnose command", body)
        self.assertIn("Diagnosis requested", body)
        self.assertNotIn("Issue:", body)
        self.assertNotIn("Title:", body)
        self.assertNotIn("<!-- clawqueue:progress -->", body)

    def test_historical_retry_with_command_result_is_not_replayed(self) -> None:
        import tempfile
        from pathlib import Path
        from types import SimpleNamespace

        comments = [
            {"id": 101, "body": "/cq retry"},
            {"id": 102, "body": "### CQ retry command\n\n- Queued for retry."},
        ]

        class Tracker:
            def list_issues(self, state: str = "open") -> list[dict]:
                return [{"number": 7, "title": "Task", "labels": [], "_repo": "owner/repo"}]

            def issue_comments(self, repo: str, number: int) -> list[dict]:
                return comments

        with tempfile.TemporaryDirectory() as tmp:
            dispatcher = ClawQueueDispatcher.__new__(ClawQueueDispatcher)
            dispatcher.config = SimpleNamespace(
                state_dir=Path(tmp),
                taskboard_repo="owner/repo",
            )
            dispatcher.tracker = Tracker()
            applied: list[tuple[str, str, int]] = []
            dispatcher.apply_slash_command = lambda command, repo, number, title, labels: applied.append(  # type: ignore[method-assign]
                (command, repo, number)
            )

            dispatcher.process_slash_commands()

            processed = dispatcher.load_processed_commands()

        self.assertEqual(applied, [])
        self.assertIn(101, processed)

    def test_historical_retry_followed_by_completion_is_not_replayed(self) -> None:
        import tempfile
        from pathlib import Path
        from types import SimpleNamespace

        done = "<!-- clawqueue:result -->\n{}\n<!-- clawqueue:done -->"
        comments = [
            {"id": 301, "body": "/cq retry"},
            {"id": 302, "body": done},
        ]

        class Tracker:
            def list_issues(self, state: str = "open") -> list[dict]:
                return [{"number": 7, "title": "Task", "labels": [], "_repo": "owner/repo"}]

            def issue_comments(self, repo: str, number: int) -> list[dict]:
                return comments

        with tempfile.TemporaryDirectory() as tmp:
            dispatcher = ClawQueueDispatcher.__new__(ClawQueueDispatcher)
            dispatcher.config = SimpleNamespace(
                state_dir=Path(tmp),
                taskboard_repo="owner/repo",
            )
            dispatcher.tracker = Tracker()
            applied: list[tuple[str, str, int]] = []
            dispatcher.apply_slash_command = lambda command, repo, number, title, labels: applied.append(  # type: ignore[method-assign]
                (command, repo, number)
            )

            dispatcher.process_slash_commands()

            processed = dispatcher.load_processed_commands()

        self.assertEqual(applied, [])
        self.assertIn(301, processed)

    def test_unacknowledged_retry_still_runs_once(self) -> None:
        import tempfile
        from pathlib import Path
        from types import SimpleNamespace

        comments = [{"id": 201, "body": "/cq retry"}]

        class Tracker:
            def list_issues(self, state: str = "open") -> list[dict]:
                return [{"number": 7, "title": "Task", "labels": [], "_repo": "owner/repo"}]

            def issue_comments(self, repo: str, number: int) -> list[dict]:
                return comments

        with tempfile.TemporaryDirectory() as tmp:
            dispatcher = ClawQueueDispatcher.__new__(ClawQueueDispatcher)
            dispatcher.config = SimpleNamespace(
                state_dir=Path(tmp),
                taskboard_repo="owner/repo",
            )
            dispatcher.tracker = Tracker()
            applied: list[tuple[str, str, int]] = []
            dispatcher.apply_slash_command = lambda command, repo, number, title, labels: applied.append(  # type: ignore[method-assign]
                (command, repo, number)
            )

            dispatcher.process_slash_commands()
            dispatcher.process_slash_commands()

        self.assertEqual(applied, [("retry", "owner/repo", 7)])


class DiagnoseTests(unittest.TestCase):
    def test_diagnose_flags_missing_openclaw_agent(self) -> None:
        import tempfile
        from pathlib import Path
        from types import SimpleNamespace

        with tempfile.TemporaryDirectory() as tmp:
            dispatcher = ClawQueueDispatcher.__new__(ClawQueueDispatcher)
            dispatcher.config = SimpleNamespace(
                mode_to_agent={"cmo": "cmo"},
                agent_provider={"manobot-cmo": "codex"},
                runner_backend="openclaw",
                openclaw_command="openclaw",
                max_attempts_per_issue=5,
                lock_file=Path(tmp) / "lock.json",
                last_run_file=Path(tmp) / "last_run",
                min_run_interval_min=2,
                resolve_agent_candidates=lambda mode_label, explicit_agent=None: ("manobot-cmo",),
            )
            dispatcher.runner = SimpleNamespace(resolve_mode=lambda labels: "cmo")
            dispatcher.tracker = SimpleNamespace(
                build_board_cache=lambda: {"silvesterxm/ClawQueue:48": {"status": "Todo"}},
                cache_key=lambda repo, number: f"{repo}:{number}",
            )
            dispatcher.active_task_key = lambda: None  # type: ignore[method-assign]
            dispatcher.get_attempt_count = lambda repo, number: 0  # type: ignore[method-assign]
            dispatcher.available_openclaw_agents = lambda: ({"main", "example-cmo"}, "")  # type: ignore[method-assign]

            state, details = dispatcher.diagnose_issue(
                "silvesterxm/ClawQueue",
                48,
                "CMO: improve public-facing README",
                ["cmo"],
            )

        text = "\n".join(details)
        self.assertEqual(state, "blocked")
        self.assertIn("OpenClaw agent `manobot-cmo` is not configured", text)
        self.assertIn("`example-cmo`", text)
        self.assertIn("resolve the blocker above", text)

class LaunchPreflightTests(unittest.TestCase):
    def test_validate_task_agent_blocks_unknown_openclaw_agent(self) -> None:
        from types import SimpleNamespace
        from clawqueue.tracker import Task

        dispatcher = ClawQueueDispatcher.__new__(ClawQueueDispatcher)
        dispatcher.config = SimpleNamespace(
            runner_backend="openclaw",
            resolve_agent_candidates=lambda mode_label, explicit_agent=None: ("manobot-cmo", "manobot-cto"),
        )
        dispatcher.available_openclaw_agents = lambda: ({"main", "manobot-cto"}, "")  # type: ignore[method-assign]
        task = Task(
            number=48,
            title="Task",
            body="",
            labels=["cmo"],
            mode_label="cmo",
            agent_name="manobot-cmo",
            priority=0,
            repo="silvesterxm/ClawQueue",
            project_name="CQC",
        )

        reason = dispatcher.validate_task_agent(task)

        self.assertIn("manobot-cmo", reason)
        self.assertIn("not configured", reason)
        self.assertIn("manobot-cto", reason)


class DeliverableTypeTests(unittest.TestCase):
    def test_explicit_deliverable_labels_win(self) -> None:
        from clawqueue.deliverables import resolve_deliverable_type

        self.assertEqual(resolve_deliverable_type(["cq:artifact"], "fix bug"), "artifact")
        self.assertEqual(resolve_deliverable_type(["cq:change"], "research report"), "change")

    def test_deliverable_type_infers_artifacts_and_changes(self) -> None:
        from clawqueue.deliverables import resolve_deliverable_type

        self.assertEqual(resolve_deliverable_type([], "Research report for board setup"), "artifact")
        self.assertEqual(resolve_deliverable_type([], "Fix weather page regression"), "change")

    def test_dispatcher_adds_missing_deliverable_label(self) -> None:
        from types import SimpleNamespace
        from clawqueue.tracker import Task

        added: list[tuple[str, int, str]] = []
        dispatcher = ClawQueueDispatcher.__new__(ClawQueueDispatcher)
        dispatcher.tracker = SimpleNamespace(add_label=lambda repo, number, label: added.append((repo, number, label)))
        task = Task(1, "Report", "", [], "cto", "manobot-cto", 0, "owner/repo", deliverable_type="artifact")

        dispatcher.ensure_deliverable_label(task)

        self.assertEqual(added, [("owner/repo", 1, "cq:artifact")])
        self.assertIn("cq:artifact", task.labels)

    def test_extract_explicit_agent_label(self) -> None:
        dispatcher = ClawQueueDispatcher.__new__(ClawQueueDispatcher)
        dispatcher.EXPLICIT_AGENT_PREFIX = "agent:"
        self.assertEqual(dispatcher.extract_explicit_agent(["cmo", "agent:manobot-cmo"]), "manobot-cmo")
        self.assertIsNone(dispatcher.extract_explicit_agent(["cmo", "todo"]))

class SafetyPolicyTests(unittest.TestCase):
    def test_change_tasks_are_blocked_for_untrusted_authors(self) -> None:
        from types import SimpleNamespace
        from clawqueue.tracker import Task

        dispatcher = ClawQueueDispatcher.__new__(ClawQueueDispatcher)
        dispatcher.config = SimpleNamespace(change_author_allowlist=("silvesterxm", "nikil511"))
        task = Task(
            number=7,
            title="Fix bug",
            body="",
            labels=["cq:change"],
            mode_label="cto",
            agent_name="manobot-cto",
            priority=0,
            repo="owner/repo",
            deliverable_type="change",
            author="random-user",
        )

        reason = dispatcher.validate_task_safety(task)

        self.assertIn("cq:change is restricted", reason)
        self.assertIn("random-user", reason)

    def test_artifact_tasks_are_not_author_restricted(self) -> None:
        from types import SimpleNamespace
        from clawqueue.tracker import Task

        dispatcher = ClawQueueDispatcher.__new__(ClawQueueDispatcher)
        dispatcher.config = SimpleNamespace(change_author_allowlist=("silvesterxm",))
        task = Task(
            number=8,
            title="Research report",
            body="",
            labels=["cq:artifact"],
            mode_label="cto",
            agent_name="manobot-cto",
            priority=0,
            repo="owner/repo",
            deliverable_type="artifact",
            author="random-user",
        )

        self.assertEqual(dispatcher.validate_task_safety(task), "")


if __name__ == "__main__":
    unittest.main()
