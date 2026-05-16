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
      "example-org/product-repo",
      "example-org/growth-or-ops-repo"
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
    "agent_roles": {
      "ceo": ["ceo"],
      "cto": ["cto"],
      "cmo": ["cmo"],
      "dev": ["dev"],
      "engineer": ["dev"],
      "researcher": ["researcher"],
      "reviewer": ["reviewer"]
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
        "retail",
        "conversion"
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
        "backfill"
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
    "deliver_channel": "telegram"
  },
  "github": {
    "reviewer_auto_closes_issue": true
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
      "repo": "example-org/clawqueue",
      "status_options": {},
      "dispatch_statuses": [
        "Todo"
      ]
    },
    "DATA": {
      "number": 3,
      "repo": "example-org/product-repo",
      "extra_repos": [
        "example-org/growth-or-ops-repo"
      ],
      "status_options": {},
      "dispatch_statuses": [
        "Todo"
      ]
    }
  }
}
---

# Company Workflow Policy

This file is the repo-owned generic workflow and routing policy for the CQ scheduler/dispatcher.

- The frontmatter is JSON, which is valid YAML syntax and easy to parse without third-party dependencies.
- It is safe to commit because it contains placeholder repo names only.
- Private GitHub Project node IDs, status option IDs, assignee names, and notification credentials belong in an untracked private config file, profile secrets, or environment variables.
- Deployments can override mode-to-agent, role-to-runtime-agent candidates (`routing.agent_roles`), agent-provider, fallback routing, projects, and repositories without editing tracked core code.

The scheduler/dispatcher loads this policy first, then merges private overrides from `config/clawqueue.private.json` if present, then applies environment variable overrides.

Default project concepts:

- `MT` covers main CQ and orchestration work.
- `GROWTH` covers sales, marketing, social, partnerships, ecommerce, campaigns, and conversion work.
- `DATA` covers data, research, dashboards, analytics, APIs, reports, metrics, and experiments.

Routing stays generic at the policy layer (`ceo`, `cto`, `cmo`, `reviewer`, `dev`). The vanilla policy maps roles to same-named local agents. Deployments should override those role-to-runtime-agent candidates with `routing.agent_roles`, for example:

```json
"agent_roles": {
  "cmo": ["manobot-cmo", "stratobot-cmo"],
  "cto": ["manobot-cto"],
  "reviewer": ["manobot-reviewer"],
  "dev": ["main"]
}
```

If one issue must hit a specific runtime agent, add an explicit label such as `agent:manobot-cmo`.

Default GitHub-native CQ board statuses should be:

- `Todo`
- `In Progress`
- `Done`

Default dispatch remains `Todo` only until a project has real board IDs/status options. When a deployment configures a `Review` status and includes `Review` in that project's `dispatch_statuses`, `cq:change` work uses the reviewed-change flow:

1. implementation agent completes the source/content/config/docs change
2. CQ moves the issue to `Review`
3. reviewer agent picks the open `Review` issue
4. if the reviewer posts `status=done` with `needs_review=false`, CQ moves the project item to `Done`

If `Review` is not configured for dispatch, Review remains a human/operator lane.

Advanced/internal profiles may extend the board manually in the GitHub UI with richer statuses such as:

- `Inbox`
- `Review`
- `Blocked`

Profiles may replace board names and keywords with company-specific boards, but they should preserve the basic queue semantics unless there is a strong reason not to.
