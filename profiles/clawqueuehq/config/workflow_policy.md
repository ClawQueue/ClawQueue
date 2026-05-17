---
{
  "runtime": {
    "all_opus": false,
    "max_attempts_per_issue": 5,
    "min_run_interval_min": 2,
    "idle_timeout_min": 0,
    "tg_ask_cooldown_min": 30,
    "openclaw_command": "openclaw"
  },
  "repositories": {
    "primary": "ClawQueue/ClawQueue",
    "extras": []
  },
  "routing": {
    "mode_priority": [
      "ceo",
      "cto",
      "reviewer",
      "cmo",
      "dev",
      "engineer"
    ],
    "analyst_modes": [
      "researcher"
    ],
    "mode_to_agent": {
      "ceo": "ceo",
      "cto": "cto",
      "cmo": "cmo",
      "dev": "dev",
      "engineer": "dev",
      "reviewer": "reviewer"
    },
    "agent_roles": {
      "ceo": ["manobot-ceo"],
      "cto": ["manobot-cto"],
      "cmo": ["manobot-cmo"],
      "dev": ["main"],
      "engineer": ["main"],
      "reviewer": ["manobot-reviewer"]
    },
    "agent_provider": {
      "ceo": "codex",
      "cto": "codex",
      "dev": "codex",
      "cmo": "codex",
      "reviewer": "codex"
    },
    "agent_fallback": {
      "cto": "ceo",
      "cmo": "cto",
      "reviewer": "cto"
    },
    "project_routing_keywords": {
      "GROWTH": [
        "docs",
        "readme",
        "launch",
        "website",
        "messaging",
        "positioning",
        "social",
        "community",
        "adoption",
        "onboarding",
        "examples",
        "research",
        "competitor",
        "operator interview",
        "feedback"
      ],
      "OPS": [
        "ops",
        "runbook",
        "release",
        "deploy",
        "launchd",
        "cron",
        "worklog",
        "artifacts",
        "diagnose",
        "self-host",
        "policy"
      ]
    }
  },
  "quota": {
    "day_stop_remaining_pct": 5,
    "night_stop_remaining_pct": 5,
    "daily_warn_remaining_pct": 10,
    "weekly_warn_remaining_pct": 20,
    "weekly_stop_remaining_pct": 0,
    "night_hours": [0, 0]
  },
  "activity": {
    "user_active_gate_min": 0,
    "athens_utc_offset_hours": 2
  },
  "artifacts": {
    "backend": "git",
    "repo": "ClawQueue/ClawQueue-reports",
    "checkout_dir": "/Users/manolis/Code/clawqueuehq-worklog",
    "path": "boards",
    "commit": true
  },
  "notifications": {
    "deliver_channel": "none"
  },
  "github": {
    "assignee": "your-github-login",
    "reviewer_auto_closes_issue": true
  },
  "safety": {
    "change_author_allowlist": [
      "your-github-login"
    ]
  },
  "projects": {
    "CORE": {
      "number": 1,
      "repo": "ClawQueue/ClawQueue",
      "project_id": "PVT_kwDOEOHfus4BXOWl",
      "field_id": "PVTSSF_lADOEOHfus4BXOWlzhScsfA",
      "status_options": {
        "inbox": "995b4525",
        "todo": "f75ad846",
        "in_progress": "47fc9ee4",
        "review": "0530f4d9",
        "done": "98236657",
        "blocked": "07da76d1"
      },
      "dispatch_statuses": ["Todo", "Review"]
    },
    "GROWTH": {
      "number": 2,
      "repo": "ClawQueue/ClawQueue",
      "status_options": {},
      "dispatch_statuses": ["Todo"]
    },
    "OPS": {
      "number": 3,
      "repo": "ClawQueue/ClawQueue",
      "status_options": {},
      "dispatch_statuses": ["Todo"]
    }
  }
}
---

# ClawQueueHQ Workflow Policy

This file is the profile-owned workflow and routing policy for ClawQueue operating on itself.

- The frontmatter is JSON, which is valid YAML syntax and easy to parse without third-party dependencies.
- It is safe to commit because it contains placeholder/self-owned repo names only.
- Private GitHub Project node IDs, status option IDs, assignee names, and notification credentials belong in an untracked private config file, `profiles/clawqueuehq/secrets/`, or environment variables.
- Deployments can override mode-to-agent, agent-provider, fallback routing, projects, and repositories without editing tracked core code.

Default project concepts:

- `CORE` covers scheduler, runner, config, repo/product, and implementation work.
- `GROWTH` covers docs, messaging, examples, adoption, launch framing, and community-facing drafts.
- `OPS` covers self-hosting, runbooks, release coordination, worklog discipline, and internal CQ operations.
