# ClawQueueHQ Profile

This profile is the internal self-operating profile for ClawQueue itself.

It adapts the workflow discipline proven in the a private operator profile profile, but points it at ClawQueue’s own mission: GitHub-native durable work, local execution, reviewable artifacts, and operator control.

## Layout

```text
profiles/clawqueuehq/
  README.md
  COMPANY.md                 # ClawQueue mission, operating principles, approval boundaries
  PRODUCT_CONTEXT.md         # compact product/system map for CQ itself
  agents/                    # ClawQueue-specific agent identities and souls
  modes/                     # task lenses for CQ work
  config/
    workflow_policy.md       # CQ self-operation routing/project policy
    clawqueue.private.example.json
  boards/<board>/BOARD_GUIDANCE.md  # optional hand-authored board guidance
  secrets/                   # ignored/private by default
```

Generated artifacts should go to a second repo dedicated to worklog/artifacts such as `ClawQueue/clawqueuehq-worklog`, not into the same branch used for core code/profile PRs.

## Using this profile

If multiple profiles exist, select it explicitly:

```bash
python3 scripts/status.py --profile clawqueuehq --no-queue
python3 scripts/scheduler.py --profile clawqueuehq
```

Or set:

```bash
export CLAWQUEUE_PROFILE=clawqueuehq
```

Or add `.clawqueue/config.yaml`:

```yaml
profile: clawqueuehq
```

## Bootstrap agents

Start with only:

- `ceo` — direction, leverage, scope challenge
- `cto` — architecture, workflow, runner/config/system design
- `cmo` — docs narrative, positioning, launch framing, adoption support

The copied `dev` and `reviewer` agents/modes are included so the full team shape is available when needed. Research work for CQ usually routes through the CMO/adoption role unless a dedicated researcher is reintroduced later.

## GitHub Project boards

Suggested CQ-self boards:

| Key | Purpose |
|---|---|
| `CORE` | scheduler, runner, config, repo/product surface |
| `GROWTH` | docs, messaging, launch framing, community, adoption |
| `OPS` | internal runbooks, self-hosting, worklog, release/readiness |

Replace placeholder repo names and private GitHub Project IDs in `config/workflow_policy.md` and an untracked private config file.

## Installation / board setup

### 1) Bootstrap labels for this profile

```bash
python3 scripts/bootstrap_github.py --profile clawqueuehq
```

### 2) Create the source-repo project board

```bash
python3 scripts/bootstrap_project_board.py \
  --owner ClawQueue \
  --title "CQ Core" \
  --key CORE \
  --repo ClawQueue/ClawQueue
```

This creates the project, ensures the default GitHub status field, links the project to the source repo, and prints the IDs/snippet you can paste into `profiles/clawqueuehq/config/workflow_policy.md`.

For agent routing, keep the policy role-based (`ceo`, `cto`, `cmo`, etc.) and map those roles to your local OpenClaw runtime ids with `routing.agent_roles`. In this profile, `cmo` can point to something like `manobot-cmo` without baking that runtime-specific name into CQ’s shared semantics.

### 3) Minimal GitHub UI setup

In the GitHub Project UI for `CQ Core`:

1. Create or keep a **Board** view
2. Set layout to **Board**
3. Group by **Status**
4. Save it as the default view

Default/simple CQ flow is:

- `Todo`
- `In Progress`
- `Done`

### 4) Optional richer internal flow

If you want the fuller CQHQ workflow, add these status options manually in the GitHub UI:

- `Inbox`
- `Review`
- `Blocked`

Then tell CQ the resulting option IDs in `workflow_policy.md` if you want automation to use them.

## Artifact storage

Recommended worklog config for CQ self-operation:

```json
"artifacts": {
  "backend": "git",
  "repo": "ClawQueue/clawqueuehq-worklog",
  "path": "boards",
  "commit": true
}
```

Do not mix generated artifacts into the same branch used for CQ code/profile PRs.

## Safety

Do not commit tokens, chat IDs, credentials, or private IDs unless that is intentionally part of a private deployment. Put sensitive deployment files under `profiles/clawqueuehq/secrets/` or provide them through environment variables.
