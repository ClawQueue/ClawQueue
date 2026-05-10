# Example CQ Profile

This is the bundled sample profile for ClawQueue. It represents a generic SaaS company with enough role flavor to demonstrate profile-specific agents, modes, routing policy, and work artifacts without exposing any real company context.

CQ core should stay generic. Real company/project context should live in a selected profile such as this one, a private deployment profile, or an untracked/private profile repository.

## Layout

```text
profiles/example/
  README.md
  COMPANY.md                 # sample SaaS mission, operating principles, approval boundaries
  PRODUCT_CONTEXT.md         # compact generic SaaS product/system map for agents
  agents/                    # example agent identities and souls
  modes/                     # example mode prompts
  config/
    workflow_policy.md       # example routing/project policy
    clawqueue.private.example.json
  boards/<board>/BOARD_GUIDANCE.md  # optional hand-authored board guidance
  secrets/                   # ignored/private by default
```

Generated artifacts should not be committed to this profile by default. They go to `.clawqueue/boards` for local installs or to a second repo dedicated to worklog/artifacts for company deployments. See [`../../docs/guide/artifacts.md`](../../docs/guide/artifacts.md).

## Using this profile

With only this profile present, CQ can auto-select it. If multiple profiles exist, choose one explicitly:

```bash
python3 scripts/status.py --profile example --no-queue
python3 scripts/scheduler.py --profile example
python3 scripts/install_launchd.py --repo "$HOME/ClawQueue" --profile example
```

Or set:

```bash
export CLAWQUEUE_PROFILE=example
```

Or add `.clawqueue/config.yaml`:

```yaml
profile: example
```

## Bootstrap agents

Start with only:

- `ceo` — strategy, leverage, scope challenge
- `cto` — product/technical architecture and execution design
- `cmo` — growth, demand, narrative, sales, marketing, social, partnerships

The copied `dev`, `researcher`, and `reviewer` agents/modes are included to show a fuller team shape, but a new operator does not need to register every role on day one.

## GitHub Project boards

The example policy uses placeholder boards:

| Key | Purpose |
|---|---|
| `MT` | Core product, orchestration, and management tasks |
| `GROWTH` | Sales, marketing, social, partnerships, and conversion work |
| `DATA` | Analytics, research, dashboards, APIs, and experiment work |

Keep the tracked policy portable. Put shared placeholders or company-owned non-secret defaults in `profiles/example/config/workflow_policy.md`; put each operator's local paths, agent IDs, assignee, notification targets, credentials, and private overrides in ignored `profiles/example/config/clawqueue.private.json`.

For shared profiles, run CQ with `--profile example` rather than `CLAWQUEUE_POLICY_FILE`; profile selection resolves `modes/`, `agents/`, and the ignored private config from each user's local checkout.

Recommended default CQ status flow for the example profile:
- Todo
- In Progress
- Done

If a real deployment wants a richer human-agent workflow, it can extend the board manually in the GitHub UI with statuses like `Inbox`, `Review`, and `Blocked`.

Bootstrap a new board with:

```bash
python3 scripts/bootstrap_project_board.py --owner your-org --title "Core Product" --key MT --repo your-org/clawqueue
```

Then paste the printed policy snippet into your profile policy.

## Artifact storage

The example profile defaults to local ignored artifacts:

```json
"artifacts": {
  "backend": "local",
  "repo": "",
  "path": ".clawqueue/boards",
  "commit": false
}
```

For a real company, prefer a second repo dedicated to worklog/artifacts:

```json
"artifacts": {
  "backend": "git",
  "repo": "your-org/clawqueue-worklog",
  "path": "boards",
  "commit": true
}
```

Do not mix generated artifacts into the same branch used for code/profile PRs.

## Safety

Do not commit tokens, chat IDs, customer data, private exports, credentials, or real board IDs unless the profile is private and that is intentional. Put sensitive deployment files under `profiles/example/secrets/` or provide them through environment variables.

## Creating your own profile

Copy this folder:

```bash
cp -R profiles/example profiles/acme
```

Then edit `COMPANY.md`, `PRODUCT_CONTEXT.md`, `agents/`, `modes/`, and `config/` for your real team.
