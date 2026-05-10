from __future__ import annotations

import json
import re
from typing import Any, Optional


PROGRESS_MARKER = "<!-- clawqueue:progress -->"
RESULT_MARKER = "<!-- clawqueue:result -->"

DEFAULT_RESULT = {
    "status": "done",
    "summary": "",
    "files_changed": [],
    "needs_review": False,
}


def progress_body(*, status: str, repo: str, issue: int, title: str, details: list[str] | None = None) -> str:
    lines = [
        PROGRESS_MARKER,
        f"### CQ status: {status}",
        "",
        f"Issue: `{repo}#{issue}`",
        f"Title: {title}",
    ]
    if details:
        lines.extend(["", *[f"- {item}" for item in details if item]])
    lines.extend(
        [
            "",
            "_Managed by ClawQueue. Commands: `/cq diagnose`, `/cq run`, `/cq retry`, `/cq pause`._",
        ]
    )
    return "\n".join(lines)


def result_contract_text(issue: int, repo: str) -> str:
    example = {
        "status": "done",
        "summary": "Brief operator-facing summary.",
        "files_changed": ["relative/path-or-artifact-url"],
        "needs_review": True,
    }
    return (
        "When finished, post exactly one completion comment. Start with a short, friendly "
        "operator-facing summary in normal Markdown, then show the pushed deliverable link(s) as "
        "clickable Markdown links, then include the hidden CQ result marker, a fenced JSON "
        "object matching this tiny result contract, and the existing done marker. CQ owns "
        "final board movement and other durable GitHub mutations.\n\n"
        f"Comment command template: `gh issue comment {issue} --repo {repo} --body '<message>'`\n\n"
        "Required completion comment shape:\n\n"
        "Done — <one concise human-readable summary>.\n\n"
        "Deliverable: [friendly label](https://github.com/owner/repo/blob/commit-or-branch/path)\n\n"
        f"{RESULT_MARKER}\n"
        "```json\n"
        f"{json.dumps(example, indent=2)}\n"
        "```\n"
        "<!-- clawqueue:done -->"
    )


def extract_result(comment_body: str) -> Optional[dict[str, Any]]:
    if RESULT_MARKER not in comment_body:
        return None
    match = re.search(r"```json\s*(\{.*?\})\s*```", comment_body, flags=re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    status = str(data.get("status", "")).strip().lower()
    if status not in {"done", "failed", "blocked", "needs_review"}:
        return None
    summary = str(data.get("summary", "")).strip()
    files_changed = data.get("files_changed", [])
    if not isinstance(files_changed, list):
        files_changed = []
    return {
        "status": status,
        "summary": summary,
        "files_changed": [str(item) for item in files_changed],
        "needs_review": bool(data.get("needs_review", status in {"done", "needs_review"})),
    }
