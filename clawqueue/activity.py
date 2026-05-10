from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from glob import glob

from .config import RuntimeConfig


class ActivityMonitor:
    def __init__(self, config: RuntimeConfig):
        self.config = config
        self.athens_tz = timezone(timedelta(hours=config.athens_utc_offset_hours))

    def is_night(self) -> bool:
        now_athens = datetime.now(timezone.utc).astimezone(self.athens_tz)
        start, end = self.config.night_hours
        if start > end:
            return now_athens.hour >= start or now_athens.hour < end
        return start <= now_athens.hour < end

    def get_stop_remaining_pct(self) -> int:
        if self.is_night():
            return self.config.night_stop_remaining_pct
        return self.config.day_stop_remaining_pct

    def get_last_user_activity(self) -> tuple[float, bool]:
        now_utc = datetime.now(timezone.utc)
        session_files = sorted(
            glob(str(self.config.sessions_dir / "*.jsonl")),
            key=os.path.getmtime,
            reverse=True,
        )
        if not session_files:
            return 999, self.is_night()

        last_user_ts = None
        for session_file in session_files[:3]:
            try:
                with open(session_file, encoding="utf-8") as handle:
                    for line in handle:
                        try:
                            record = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        message = record.get("message")
                        if not isinstance(message, dict) or message.get("role") != "user":
                            continue
                        content = message.get("content", "")
                        if isinstance(content, list):
                            content_str = " ".join(
                                block.get("text", "") if isinstance(block, dict) else str(block)
                                for block in content
                            )
                        else:
                            content_str = str(content) if content else ""
                        if self._is_system_message(content_str):
                            continue
                        ts_str = record.get("timestamp", "")
                        if not ts_str:
                            continue
                        try:
                            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                        except ValueError:
                            continue
                        if last_user_ts is None or ts > last_user_ts:
                            last_user_ts = ts
            except OSError:
                continue

        if last_user_ts is None:
            return 999, self.is_night()
        minutes_ago = (now_utc - last_user_ts).total_seconds() / 60
        return round(minutes_ago, 1), self.is_night()

    @staticmethod
    def _is_system_message(content: str) -> bool:
        markers = (
            "A scheduled reminder",
            "HEARTBEAT",
            "Read HEARTBEAT",
            "system event",
            "[Queued messages",
            "scheduled reminder has been triggered",
            "Exec completed (",
            "Exec failed (",
            "System: [",
            "Pre-compaction memory flush",
            "Post-compaction context refresh",
            "Session was just compacted",
            "[cron:",
        )
        lowered = content.lower()
        return any(marker in content for marker in markers) or "system event" in lowered
