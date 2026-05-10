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
profiles/<profile>/secrets/
```

Keep these private:

- GitHub ProjectV2 node IDs
- status field and option IDs
- personal assignee names
- Telegram or chat tokens
- notification targets
- local machine paths
- local runner/agent IDs when they reveal private infrastructure

## Environment variables

Environment variables can override private config for CI or secret-managed hosts.
The example config documents the supported shape.

## Public-repo rule

Before publishing or pushing to a public repo, run a scanner such as gitleaks,
TruffleHog, or detect-secrets. ClawQueue is built around local automation, so
accidentally committing private IDs or tokens is the easiest way to ruin your day.
