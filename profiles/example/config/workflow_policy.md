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
    "primary": "example-org/clawqueue",
    "extras": [
      "example-org/product-app",
      "example-org/growth-site"
    ]
  },
  "routing": {
    "mode_priority": [
      "ceo",
      "cto",
      "reviewer",
      "cmo",
      "researcher",
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
      "researcher": "researcher",
      "reviewer": "reviewer"
    },
    "agent_provider": {
      "ceo": "codex",
      "cto": "codex",
      "dev": "codex",
      "cmo": "codex",
      "researcher": "codex",
      "reviewer": "codex"
    },
    "agent_fallback": {
      "cto": "ceo",
      "cmo": "cto",
      "researcher": "cto",
      "reviewer": "cto"
    },
    "project_routing_keywords": {
      "GROWTH": [
        "sales",
        "marketing",
        "social",
        "campaign",
        "partnership",
        "lead",
        "pipeline",
        "outreach",
        "crm",
        "seo",
        "landing page",
        "page copy",
        "product page",
        "analytics",
        "email",
        "conversion",
        "pricing",
        "positioning"
      ],
      "DATA": [
        "data",
        "research",
        "dashboard",
        "analytics",
        "api",
        "dataset",
        "report",
        "metrics",
        "model",
        "evaluation",
        "experiment",
        "backfill",
        "customer interview",
        "retention",
        "activation"
      ]
    }
  },
  "quota": {
    "day_stop_remaining_pct": 5,
    "night_stop_remaining_pct": 5,
    "daily_warn_remaining_pct": 10,
    "weekly_warn_remaining_pct": 20,
    "weekly_stop_remaining_pct": 0,
    "night_hours": [
      0,
      0
    ]
  },
  "activity": {
    "user_active_gate_min": 0,
    "athens_utc_offset_hours": 2
  },
  "artifacts": {
    "backend": "local",
    "repo": "",
    "path": ".clawqueue/boards",
    "commit": false
  },
  "notifications": {
    "deliver_channel": "none"
  },
  "github": {
    "assignee": "your-github-login",
    "reviewer_auto_closes_issue": true
  },
  "review": {
    "default_level": "standard",
    "levels": ["standard", "extra"],
    "extra_review_required": false
  },
  "safety": {
    "change_author_allowlist": [
      "your-github-login"
    ]
  },
  "projects": {
    "MT": {
      "number": 1,
      "repo": "example-org/clawqueue",
      "status_options": {},
      "dispatch_statuses": [
        "Todo"
      ]
    },
    "GROWTH": {
      "number": 2,
      "repo": "example-org/growth-site",
      "status_options": {},
      "dispatch_statuses": [
        "Todo"
      ]
    },
    "DATA": {
      "number": 3,
      "repo": "example-org/product-app",
      "extra_repos": [
        "example-org/growth-site"
      ],
      "status_options": {},
      "dispatch_statuses": [
        "Todo"
      ]
    }
  }
}
---

# Example SaaS Workflow Policy

This file is the profile-owned workflow and routing policy for the bundled example SaaS company.

- The frontmatter is JSON, which is valid YAML syntax and easy to parse without third-party dependencies.
- It is safe to commit because it contains placeholder repo names only.
- Private GitHub Project node IDs, status option IDs, assignee names, notification credentials, local agent IDs, and machine-specific paths belong in ignored `profiles/example/config/clawqueue.private.json`, `profiles/example/secrets/`, or environment variables.
- Shared deployments should run with `--profile example`, not only `CLAWQUEUE_POLICY_FILE`, so CQ resolves profile-relative modes/agents and each operator's ignored private config from their own checkout.
- Deployments can override mode-to-agent, agent-provider, fallback routing, projects, repositories, artifacts, and notifications without editing tracked core code.

Default project concepts:

- `MT` covers ClawQueue/core management and product orchestration work.
- `GROWTH` covers sales, marketing, social, partnerships, campaigns, and conversion work.
- `DATA` covers analytics, customer research, dashboards, APIs, reports, metrics, and experiments.

Default CQ status flow for these boards should be:

- `Todo`
- `In Progress`
- `Done`

Dispatch should default to `Todo` only.

If a real deployment wants a richer human-agent workflow, it can extend the board manually in the GitHub UI with statuses like `Inbox`, `Review`, and `Blocked`.

Copy this profile before using CQ for a real company. Commit shared/company-safe defaults; keep per-user local config ignored.
