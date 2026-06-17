---
type: Guide
title: Configuration
description: Public policy and private configuration split.
tags: [configuration, config, policy, secrets]
timestamp: 2026-06-17T16:28:00Z
---

# Configuration

ClawQueue keeps public workflow policy separate from private deployment values.
That split is the whole safety story.

## Public policy

Public policy can live in tracked markdown/config files, for example:

```text
config/company_workflow_policy.md
profiles/<profile>/config/workflow_policy.md
```

Use public policy for conventions that are safe to share:

- labels that map to roles or modes
- dispatch status names such as `Todo` or `Review`
- dependency and review conventions
- agent-output expectations

## Private config

Private deployment values should stay out of git history:

```text
config/clawqueue.private.json
profiles/<profile>/config/clawqueue.private.json
profiles/<profile>/secrets/
```

Keep these private:

- GitHub ProjectV2 node IDs
- status field and option IDs
- personal assignee names
- Telegram or chat tokens
- notification targets
- local machine paths
- local runner/agent IDs and role mappings

## Environment variables

Environment variables can override private config for CI or secret-managed hosts.
The example config documents the supported shape.

For shared profiles, prefer `--profile <name>` over `CLAWQUEUE_POLICY_FILE`. Profile selection loads `profiles/<name>/config/workflow_policy.md`, resolves profile-relative paths such as `modes/` and `agents/`, and merges ignored `profiles/<name>/config/clawqueue.private.json` from each operator's checkout.

## Public-repo rule

Before publishing or pushing to a public repo, run a scanner such as gitleaks,
TruffleHog, or detect-secrets. ClawQueue is built around local automation, so
accidentally committing private IDs or tokens is the easiest way to ruin your day.
