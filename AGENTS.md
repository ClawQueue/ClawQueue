# AGENTS.md - ClawQueue

ClawQueue (CQ) is a generic orchestration repository for human-agent teams. It connects GitHub Issues/Projects, agent profiles, mode prompts, local state, and runner backends so humans and agents can share durable work safely.

Domain product code should live in the relevant product repository. CQ owns the workflow layer around work intake, routing, dispatch, review flow, and the roadmap for improving that system.

## Current Direction

CQ should mature as a vanilla project that can be used by many companies or teams. Company flavor belongs in a separate profile folder or private deployment repo so CQ core can be upgraded without losing local identity, routing, or private context.

Company-specific material belongs in `profiles/<company-or-team>/` or a private profile repo. Do not add company assumptions to CQ core unless the work is explicitly about a profile example.

Use **CQ** as the short name for ClawQueue in docs and issues.

## Profile Architecture

Company/team-specific data belongs under `profiles/<company-or-team>/` or an equivalent private profile repo mounted into a deployment.

Suggested profile layout:

```text
profiles/<company-or-team>/
  COMPANY.md              <- mission, vocabulary, approval boundaries
  agents/                 <- deployment-specific agent identities and souls
    ceo/IDENTITY.md
    ceo/SOUL.md
    cto/IDENTITY.md
    cto/SOUL.md
    cmo/IDENTITY.md
    cmo/SOUL.md
  modes/                  <- optional mode prompt overrides
  config/                 <- non-secret repo/project/routing config
  secrets/                <- ignored/private credentials and sensitive IDs
```

`profiles/**/secrets/` must stay ignored/private. Tokens, private ProjectV2 IDs, chat IDs, customer data, and local credentials do not belong in CQ core.

## What CQ Core Owns

- GitHub issue and ProjectV2 board orchestration.
- Scheduled task pickup, locking, stale-work sweeping, provider quota checks, and worker dispatch.
- Generic agent/mode conventions and default examples.
- Runner prompt construction and backend launch behavior.
- Local state tooling for queue visibility and operator debugging.
- Documentation for operating CQ safely.
- Roadmap for maturing CQ into a durable company-agent workflow system.

## What CQ Core Does Not Own

- Product application code.
- Company-specific strategy, customer data, private wiki content, or proprietary operating context.
- Credentials, private ProjectV2 IDs, personal paths, tokens, or chat IDs.
- Autonomous external publishing or official company commitments.
- Secure multi-tenant execution.

## Bootstrap Workflow For New Operators

Start small and test CQ on real work:

1. Create a company/team profile or private deployment folder.
2. Register only the minimum agents first: `ceo`, `cto`, and `cmo`.
3. Configure GitHub repo/project/labels and any private IDs in the profile config or ignored secrets.
4. Create one tiny issue in `Todo` and run `python3 scripts/scheduler.py` manually.
5. Once manual dispatch is reliable, run the scheduler periodically with cron/launchd.
6. Keep concurrency at `1` until durable run state, duplicate prevention, and workspace isolation are implemented.

See `docs/guide/operator-workflow.md`, `docs/guide/artifacts.md`, and `profiles/README.md` for newcomer setup, artifact policy, and profile conventions.

## Agent Operating Rule

When a human asks for heavy work:

1. Shape it into a GitHub issue before implementation.
2. Include objective, why, scope, out of scope, acceptance criteria, validation, dependencies, and agent notes.
3. Put the issue on the corresponding project board in `Todo`.
4. Let the CQ scheduler/orchestrator pick issues one by one.
5. Improve CQ itself whenever the workflow is painful, unclear, or too manual.

Small conversational help can stay in chat. Durable, risky, or multi-step work should go through CQ.

## Durable Artifact Rule

If a task produces a Markdown/report deliverable, store it in the configured artifact destination rather than leaving it only in an agent workspace or issue comment.

Default local path:

```text
.clawqueue/boards/issues/<board>/<zero-padded-issue-number>-<slug>.md
.clawqueue/boards/issues/<board>/<zero-padded-issue-number>-<slug>/README.md
```

Company deployments that want durable git history for generated deliverables should use a second repo dedicated to artifacts/worklog, not the same branch used for product/profile PRs:

```json
"artifacts": {
  "backend": "git",
  "repo": "org/clawqueue-worklog",
  "path": "boards",
  "commit": true
}
```

Use the flat `.md` path for a single Markdown deliverable. Use a folder with `README.md` only when the task has assets, diagrams, data files, exports, or multiple deliverables. Zero-pad issue numbers to 4 digits, e.g. `0044-dlr-market-research.md`, so artifact lists sort cleanly beyond issue #99.

Before posting `<!-- clawqueue:done -->`, the worker must:

1. `git add` only exact task-scoped source files and/or artifact files in the configured artifact destination.
2. Commit and push artifact files only when the artifact destination is a git worklog repo.
3. Link pushed source-change URLs and/or artifact-worklog blob URLs in the completion comment.

Never link to local-only paths, unpushed commits, or unrelated bundled changes from a completion comment.

## Key Files

```text
AGENTS.md                 <- agent-facing operating rules for this repo
README.md                 <- product overview and architecture
ROADMAP.md                <- CQ maturation milestones
docs/guide/operator-workflow.md <- newcomer/operator setup and workflow
docs/guide/artifacts.md     <- second-repo/worklog artifact policy
profiles/README.md        <- profile/private deployment conventions

scripts/
  scheduler.py            <- Scheduler entry point
  status.py               <- Local state, decision log, and queue summary

clawqueue/
  config.py               <- Repo policy, private/profile config, env loading
  tracker.py              <- GitHub issue and ProjectV2 client
  dispatcher.py           <- Locking, sweeps, picking, dispatch flow
  runner.py               <- Agent prompt and process launcher
  activity.py             <- Local user activity gate
  notifications.py        <- Optional notification hooks
  shell.py                <- Shell command helper

agents/                   <- Current built-in/default agent examples
modes/                    <- Current built-in/default mode prompts
config/                   <- Generic workflow policy and private config examples
profiles/                 <- Company/team flavor convention; secrets ignored
```

## Agent Routing

Default label routing keeps a small functional leadership team:

| GitHub Label | Agent | Mode Prompt | Primary Use |
|---|---|---|---|
| `ceo` | ceo | `modes/ceo.md` | Strategy, mission leverage, scope challenge |
| `cto` | cto | `modes/cto.md` | Product/technical architecture and execution plans |
| `dev` | dev | none | Scoped implementation |
| `engineer` | dev | none | Scoped implementation |
| `cmo` | cmo | `modes/cmo.md` | Growth, demand, sales, marketing, social, partnerships |
| `researcher` | researcher | `modes/researcher.md` | Market, customer, technical, scientific, and evidence research |
| `reviewer` | reviewer | `modes/reviewer.md` | Review, risk, claims, approval boundaries |

Provider/model mapping is runtime configuration, not a hardcoded contract. See `clawqueue.config` and `config/company_workflow_policy.md`. Use private config or environment JSON maps when a deployment needs different mode-to-agent, provider, or fallback routing.

## Work Taxonomy

Use these categories in issue text or labels to frame the work:

- `strategy`
- `product`
- `engineering`
- `data-research`
- `sales`
- `marketing`
- `social`
- `partnerships`
- `ops`
- `review`

These categories describe the task. They do not replace routing labels unless the dispatcher is extended later.

## Workflow

1. A human or agent creates a GitHub issue with clear scope, category, acceptance criteria, and approval needs.
2. The scheduler entrypoint scans configured repos and dispatches only board items whose status is listed in that project’s `dispatch_statuses` policy. Default is `Todo`.
3. The dispatcher skips work when a lock, active worker, throttle, attempt cap, activity gate, or quota guard says to wait.
4. The selected issue is assigned, moved to `In Progress`, and launched through the configured OpenClaw agent.
5. The worker comments completion and exits.
6. Sweep logic moves stale completed implementation work to `Review` where configured, or back to `Todo` when orphaned.
7. Review behavior is profile policy: by default Review is a human/operator lane unless a deployment explicitly includes it in `dispatch_statuses` or queues a separate `Todo` review issue.

## Project Boards

CQ core should describe project-board concepts generically. Deployments may define profile-specific board names such as `Core`, `Growth`, `Data`, or company-specific abbreviations.

Real repo names, GitHub ProjectV2 node IDs, status field IDs, status option IDs, assignees, and notification details must come from profile config, ignored secret files, or environment variables.

## Approval Boundaries

Agents must not publish, send outreach, set pricing, make legal/financial/regulatory claims, or promise official roadmap, product, delivery, or partnership commitments without human approval.

External-facing deliverables should be marked as drafts until a human approves them.

## Development Notes

- Keep routing changes synchronized across `clawqueue.config`, `config/company_workflow_policy.md`, `README.md`, `modes/README.md`, `docs/guide/operator-workflow.md`, and this file.
- Keep generic prompt/persona changes suitable for CQ core; put company-specific souls and prompt overrides in profiles.
- Before sharing, scan for private IDs, tokens, chat IDs, assignees, personal absolute paths, and company-specific context that belongs in a profile.

## Don't

- Don't put domain product code here.
- Don't commit bot tokens, chat IDs, ProjectV2 node IDs, option IDs, or personal absolute paths.
- Don't change scheduler/dispatcher routing without updating tracked policy and docs.
- Don't treat this dispatcher as secure multi-tenant infrastructure without additional security work.
- Don't let agents act as official external spokespeople without human approval.
