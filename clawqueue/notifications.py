from __future__ import annotations

import json
import re
import shlex
from datetime import datetime, timezone
from urllib import parse, request

from .config import RuntimeConfig
from .shell import run_cmd
from .tracker import Task


class TelegramNotifier:
    def __init__(self, config: RuntimeConfig):
        self.config = config

    def ask_user_permission(self, task: Task) -> bool:
        if not self.config.telegram_bot_token or not self.config.telegram_chat_id:
            return False

        cooldown_file = self.config.tg_ask_cooldown_file
        if cooldown_file.exists():
            try:
                asked_at = datetime.fromisoformat(cooldown_file.read_text().strip())
                elapsed = (datetime.now(timezone.utc) - asked_at).total_seconds() / 60
                if elapsed < self.config.tg_ask_cooldown_min:
                    print(
                        f"⏸ Telegram ask cooldown: asked {elapsed:.0f}min ago "
                        f"(cooldown={self.config.tg_ask_cooldown_min}min)"
                    )
                    return False
            except (ValueError, OSError):
                pass

        message = (
            "🔥 ClawQueue has a task ready:\n\n"
            f"*#{task.number}* — {task.title}\n"
            f"Mode: `{task.mode_label}` → Agent: `{task.agent_name}`\n\n"
            "You seem active — should I kick this off? Reply *yes* or *no*"
        )
        url = f"https://api.telegram.org/bot{self.config.telegram_bot_token}/sendMessage"
        payload = parse.urlencode(
            {
                "chat_id": self.config.telegram_chat_id,
                "text": message,
                "parse_mode": "Markdown",
            }
        ).encode()
        try:
            req = request.Request(url, data=payload, method="POST")
            response = request.urlopen(req, timeout=10)
            ok = response.status == 200
        except Exception as exc:
            print(f"⚠️ Telegram send failed: {exc}")
            ok = False

        if ok:
            cooldown_file.write_text(datetime.now(timezone.utc).isoformat())
            return True
        return False

    def notify_completion(self, repo: str, issue_number: int, title: str, status: str, comments: list) -> bool:
        """Best-effort completion notification. Never blocks CQ completion."""
        channel = (self.config.completion_notify_channel or "").strip().lower()
        if not channel:
            return False

        target = (self.config.completion_notify_target or "").strip()
        if target in {"", "last-telegram"} and channel == "telegram":
            target = self.resolve_telegram_target() or ""
        if not target:
            print("⚠️ Completion notification skipped: no target found")
            return False

        deliverable = self.extract_artifact_url(comments)
        issue_url = f"https://github.com/{repo}/issues/{issue_number}"
        lines = [
            f"✅ CQ completed #{issue_number}: {title}",
            f"Status: {status}",
            f"Issue: {issue_url}",
        ]
        if deliverable:
            lines.append(f"Deliverable: {deliverable}")
        message = "\n".join(lines)

        cmd = (
            f"{shlex.quote(self.config.openclaw_command)} message send "
            f"--channel {shlex.quote(channel)} "
            f"--target {shlex.quote(target)} "
            f"--message {shlex.quote(message)} --json"
        )
        out, rc = run_cmd(cmd, timeout=30)
        if rc != 0:
            print(f"⚠️ Completion notification failed: {out[:300]}")
            return False
        if channel == "telegram":
            self.write_last_telegram_target(target)
        print(f"📣 Completion notification sent to {channel}:{target}")
        return True

    def extract_artifact_url(self, comments: list) -> str:
        urls: list[str] = []
        for comment in reversed(comments or []):
            body = str((comment or {}).get("body", ""))
            urls.extend(match.rstrip(".)]\"'") for match in re.findall(r"https://github\.com/\S+/blob/\S+", body))

        canonical = self.preferred_artifact_url(urls)
        if canonical:
            return canonical
        return urls[0] if urls else ""

    def preferred_artifact_url(self, urls: list[str]) -> str:
        artifact_repo = str(getattr(self.config, "artifact_repo", "") or "").strip()
        artifact_path = str(getattr(self.config, "artifact_path", "") or "").strip().strip("/")
        if not artifact_repo:
            return ""

        repo_prefix = f"https://github.com/{artifact_repo}/blob/"
        for url in urls:
            if not url.startswith(repo_prefix):
                continue
            rest = url[len(repo_prefix) :]
            branch_or_sha, sep, path = rest.partition("/")
            if not sep or not path:
                continue
            if artifact_path and not path.startswith(f"{artifact_path}/"):
                continue
            # Notifications should point at the canonical moving branch, not a
            # one-off commit URL from a worker result comment.
            return f"{repo_prefix}main/{path}"
        return ""

    def resolve_telegram_target(self) -> str:
        remembered = self.read_last_telegram_target()
        if remembered:
            return remembered
        discovered = self.last_telegram_target()
        if discovered:
            self.write_last_telegram_target(discovered)
        return discovered

    def read_last_telegram_target(self) -> str:
        path = self.config.last_telegram_target_file
        try:
            target = path.read_text(encoding="utf-8").strip()
        except OSError:
            return ""
        return target if re.fullmatch(r"-?\d+", target) else ""

    def write_last_telegram_target(self, target: str) -> None:
        if not re.fullmatch(r"-?\d+", target or ""):
            return
        try:
            self.config.last_telegram_target_file.write_text(target, encoding="utf-8")
        except OSError:
            pass

    def last_telegram_target(self) -> str:
        for path in sorted(self.config.sessions_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)[:12]:
            try:
                for line in reversed(path.read_text(encoding="utf-8", errors="replace").splitlines()[-80:]):
                    if 'telegram' not in line and 'chat_id' not in line:
                        continue
                    for pattern in (
                        r'"chat_id"\s*:\s*"telegram:(-?\d+)"',
                        r'"chat_id"\s*:\s*"(-?\d+)"',
                        r'agent:[^:]+:telegram:direct:([^:"]+)',
                    ):
                        m = re.search(pattern, line)
                        if m:
                            target = m.group(1)
                            if re.fullmatch(r"-?\d+", target):
                                return target
            except OSError:
                continue

        out, rc = run_cmd(
            f"{shlex.quote(self.config.openclaw_command)} sessions --json --all-agents --limit 100",
            timeout=20,
        )
        if rc != 0 or not out:
            return ""
        try:
            data = json.loads(out)
        except json.JSONDecodeError:
            return ""
        sessions = data.get("sessions") if isinstance(data, dict) else data
        if not isinstance(sessions, list):
            return ""

        newest: tuple[int, str] | None = None
        for session in sessions:
            if not isinstance(session, dict):
                continue
            key = str(session.get("key", ""))
            match = re.search(r"agent:[^:]+:telegram:direct:([^:]+)$", key)
            if not match:
                continue
            updated_at = int(session.get("updatedAt") or 0)
            target = match.group(1)
            if re.fullmatch(r"-?\d+", target) and (newest is None or updated_at > newest[0]):
                newest = (updated_at, target)
        return newest[1] if newest else ""
