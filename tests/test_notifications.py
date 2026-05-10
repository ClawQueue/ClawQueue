from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase, mock

from clawqueue.notifications import TelegramNotifier


class TelegramNotifierTests(TestCase):
    def make_config(self, tmp: str):
        return SimpleNamespace(
            completion_notify_channel="telegram",
            completion_notify_target="last-telegram",
            openclaw_command="openclaw",
            sessions_dir=Path(tmp) / "sessions",
            last_telegram_target_file=Path(tmp) / "clawqueue_last_telegram_target",
            telegram_bot_token=None,
            telegram_chat_id=None,
            tg_ask_cooldown_file=Path(tmp) / "clawqueue_tg_asked",
            tg_ask_cooldown_min=30,
        )

    def test_resolve_telegram_target_prefers_remembered_local_target(self):
        with TemporaryDirectory() as tmp:
            cfg = self.make_config(tmp)
            cfg.sessions_dir.mkdir(parents=True, exist_ok=True)
            cfg.last_telegram_target_file.write_text("12345", encoding="utf-8")
            notifier = TelegramNotifier(cfg)
            self.assertEqual(notifier.resolve_telegram_target(), "12345")

    def test_last_telegram_target_reads_recent_session_logs(self):
        with TemporaryDirectory() as tmp:
            cfg = self.make_config(tmp)
            cfg.sessions_dir.mkdir(parents=True, exist_ok=True)
            (cfg.sessions_dir / "a.jsonl").write_text(
                '{"chat_id":"telegram:1384688277","channel":"telegram"}\n',
                encoding="utf-8",
            )
            notifier = TelegramNotifier(cfg)
            self.assertEqual(notifier.last_telegram_target(), "1384688277")

    def test_notify_completion_persists_successful_telegram_target(self):
        with TemporaryDirectory() as tmp:
            cfg = self.make_config(tmp)
            cfg.sessions_dir.mkdir(parents=True, exist_ok=True)
            cfg.last_telegram_target_file.write_text("1384688277", encoding="utf-8")
            notifier = TelegramNotifier(cfg)
            with mock.patch("clawqueue.notifications.run_cmd", return_value=("{}", 0)):
                ok = notifier.notify_completion("org/repo", 1, "title", "Review", [])
            self.assertTrue(ok)
            self.assertEqual(
                cfg.last_telegram_target_file.read_text(encoding="utf-8").strip(),
                "1384688277",
            )
