# CQ Operator Workflow

CQ (ClawQueue) is a GitHub issue dispatcher for human-agent teams. The recommended operating model is simple: humans and assistants shape work into issues, GitHub Projects is the queue, and the CQ scheduler periodically picks eligible issues from configured dispatch statuses and launches the right agent.

This document is for a newcomer setting up or operating CQ. It is also the best file to hand to a fresh OpenClaw installation when you want it to install CQ and explain the workflow back to you.

## Give this to OpenClaw

If you are setting up CQ through OpenClaw, paste or point OpenClaw at this file and use a request like:

> Read `docs/guide/operator-workflow.md`, inspect this repository, install/configure ClawQueue for the target profile, run one safe manual status/scheduler check, and explain back how the CQ process works before enabling launchd/cron automation.

A good OpenClaw setup response should cover:

- which repo/profile is active
- which GitHub repo and Project board are the durable queue
- which labels route to which roles/agents
- which board statuses are dispatchable
- where artifacts/worklogs go
- how to run `scripts/status.py` and `scripts/scheduler.py` manually
- what must be true before installing launchd/cron
- what safety boundaries require human approval

Do not enable periodic automation until one manual scheduler run is understandable and safe.

## Core idea

1. A human or assistant turns substantial work into a structured GitHub issue.
2. The issue is placed on the relevant GitHub Project board in `Todo`.
3. CQ's scheduler runs manually or from cron/launchd.
4. Each scheduler tick checks configured dispatch statuses and dispatches at most one eligible issue. The default profile policy is `Todo` only.
5. The worker agent comments completion using CQ's completion marker.
6. CQ moves completed work to Review and closes the GitHub issue when auto-close is enabled.
7. Humans review while the issue is closed, then either drag Review → Done or reopen it in Review for revision.

Use chat for discussion. Use issues for durable work.

### Board guidance

Boards may optionally define `profiles/<profile>/work/issues/<board>/BOARD_GUIDANCE.md`. CQ injects that file into the worker prompt as trusted runtime guidance for that board only. Use it for board-specific conventions, dependency-reading rules, and deep-repo exploration pointers.

Recommended state convention:

| GitHub issue | Board status | Meaning | Scheduler behavior |
|---|---|---|---|
| Open | Todo/Ready | New work | Eligible if configured |
| Open | In Progress | Worker active | Wait |
| Closed | Review | Deliverable ready; human review pending | Wait |
| Open | Review | Changes requested / revision needed | Eligible if Review is configured |
| Closed | Done | Accepted/final | Wait |

Avoid moving review feedback back to Todo by default: Todo means new/unstarted work; reopened Review means revise an existing deliverable using human comments.

## Recommended bootstrap path

### 1. Choose the deployment shape

CQ should stay generic. Company-specific identity should live in a profile folder or private deployment repo.

Recommended layout:

```text
clawqueue/                  # CQ core: generic dispatcher, docs, default examples
profiles/
  README.md                 # profile conventions
  <company-or-team>/        # private or deployment-specific profile
    COMPANY.md              # company mission, boundaries, vocabulary
    agents/                 # agent identities and souls for this deployment
      ceo/
      cto/
      cmo/
    modes/                  # optional mode prompt overrides
    config/                 # non-secret project/repo/routing config
    secrets/                # ignored/private by default
```

The profile folder may live inside a private fork/clone or in a separate private repo that is copied/symlinked into a CQ deployment. Keep secrets out of tracked core files.

### 2. Start with the minimum leadership team

Begin with three agents:

- `ceo` — decides whether the work should exist, challenges scope, links work to company outcomes.
- `cto` — turns approved work into robust product/technical plans and implementation tasks.
- `cmo` — handles growth, positioning, campaigns, sales, social, partnerships, and external-facing drafts.

Add `dev`, `reviewer`, `researcher`, or other specialist agents only after the queue flow works. Too many agents too early creates bureaucracy without throughput.

### 3. Configure GitHub as the queue

Create or select:

- one GitHub repository for issues
- one GitHub Project board
- status columns such as `Todo`, `In Progress`, optional `Review`, and `Done`
- labels matching the active agents/modes, initially `ceo`, `cto`, and `cmo`

Deployment-specific IDs, repo names, assignees, notification targets, and credentials belong in the profile config or ignored secret files, not in generic CQ docs.

Keep agent routing split into two layers:

- shared role names in labels/policy: `ceo`, `cto`, `cmo`, `reviewer`, `dev`
- deployment-local runtime agent ids in `routing.agent_roles`, e.g. `"cmo": ["manobot-cmo", "stratobot-cmo"]`

That keeps profiles portable across different OpenClaw installs. If one issue must hit a specific runtime agent, add a label like `agent:manobot-cmo`.

### 4. Run the scheduler manually first

From the CQ repo:

```bash
python3 scripts/status.py --no-queue
python3 scripts/scheduler.py
```

Then test with one tiny issue before enabling automation.

Validation checklist:

- issue is open and unassigned
- issue is on a board status allowed by that project’s `dispatch_statuses` policy; default is `Todo`
- explicit `depends on Issue #N` / `depends on #N` dependencies are complete after their latest retry
- labels route to the expected mode/agent
- scheduler dispatches only one issue
- status moves to `In Progress`
- worker leaves a completion comment
- sweep/review behavior is understandable

### 5. Install the scheduler

After one manual run works, install a periodic scheduler. On macOS, prefer `launchd` over cron. Keep the repo outside privacy-protected folders such as `~/Documents` or `~/Desktop`; `~/ClawQueue` is a good default. Config paths may use `$HOME`, `${HOME}`, or `~`; avoid hardcoded `/Users/<name>/...` paths.

Quick install:

```bash
python3 scripts/install_launchd.py --repo "$HOME/ClawQueue" --policy config/company_workflow_policy.md
# or profile policy:
python3 scripts/install_launchd.py --repo "$HOME/ClawQueue" --policy profiles/<profile>/config/workflow_policy.md
```

Validate/operate:

```bash
launchctl print gui/$(id -u)/com.clawqueue.scheduler | sed -n '1,80p'
launchctl kickstart -k gui/$(id -u)/com.clawqueue.scheduler
tail -50 "$HOME/.openclaw/tmp/clawqueue/scheduler-launchd.err.log"
CLAWQUEUE_POLICY_FILE="$HOME/ClawQueue/config/company_workflow_policy.md" python3 scripts/status.py
```

The installer writes:

- `~/Library/LaunchAgents/com.clawqueue.scheduler.plist`
- `~/.openclaw/service-env/clawqueue-scheduler.sh`
- logs under `~/.openclaw/tmp/clawqueue/`

Cron is fine for non-macOS hosts or personal preference, but keep it as a fallback path. Minimal cron shape:

```cron
*/5 * * * * cd "$HOME/ClawQueue" && CLAWQUEUE_POLICY_FILE="$HOME/ClawQueue/config/company_workflow_policy.md" /usr/bin/python3 scripts/scheduler.py >> "$HOME/.openclaw/tmp/clawqueue/scheduler-cron.log" 2>&1 # CQ scheduler
```

Conservative starting policy:

- run every 2-5 minutes
- keep concurrency at `1`
- keep review optional until the flow is proven
- prefer visible logs/status over silent automation

Do not raise concurrency until CQ has durable run state, duplicate-execution protection, and workspace isolation.

### 6. Completion notifications

Worker completion must not depend on chat delivery. The durable completion path is:

1. worker writes/commits/pushes task deliverables when needed
2. worker comments on the GitHub issue with `<!-- clawqueue:done -->`
3. every scheduler tick reconciles active tasks that already posted the done marker, even if the wrapper process or active marker outlived the useful work
4. CQ sweep moves the board status and removes assignment
5. CQ may send a **best-effort** notification

Configure notifications in the active workflow policy when you want them. Keep them best-effort: a failed chat send must not roll back GitHub completion or board movement.


## Agents, modes, and memory

CQ separates persistent identity from temporary task framing:

- **Chief of staff / orchestrator** — the main conversational assistant stays close to the human, turns messy discussion into CQ-ready issues, chooses the right profile/agent/mode, and summarizes outcomes back to the human.
- **Profile agents** — named OpenClaw agents such as `ceo`, `cto`, and `cmo` are persistent role specialists. They can have their own identity, soul, workspace, and memory, so each role can improve independently over time.
- **Modes** — mode files are temporary cognitive lenses injected into a task prompt. They are not a replacement for persistent agents. They are especially useful for direct `codex` or `claude` runner calls, where the CLI invocation should be treated as mostly stateless unless the external tool provides its own session/memory layer.
- **Issues** — GitHub issues are the durable shared work contract. They carry objective, scope, acceptance criteria, validation, comments, and completion history across agents and runs.
- **Profiles** — profiles carry company-specific context: mission, agent souls, mode overrides, routing policy, and private deployment conventions.

Recommended pattern:

```text
Human discussion
  -> chief of staff drafts/refines a GitHub issue
  -> CQ scheduler picks one eligible issue
  -> persistent profile agent executes with the relevant mode lens
  -> result is written back to the issue
  -> important lessons are distilled into profile/agent memory or docs
```

Do not make the chief-of-staff assistant simply “wear every hat” for all heavy work. That centralizes context, but it prevents specialist agents from developing useful role memory and turns CQ into fake orchestration. Use the chief of staff for intake, shaping, and synthesis; use profile agents for durable execution.

Memory should be layered rather than trapped in one agent:

1. GitHub issue history — canonical task state and completion evidence.
2. CQ logs/run state — operational debugging.
3. Profile docs/worklog — company-specific durable guidance and artifacts.
4. Specialist agent memory — role-specific habits and lessons.
5. Chief-of-staff memory — human preferences, workflow decisions, and cross-agent synthesis.

## Working rule for heavy work

When a human asks for heavy work:

1. Draft or refine a GitHub issue first.
2. Include objective, why, scope, out of scope, acceptance criteria, validation, dependencies, and agent notes.
3. Put the issue on the right board status for that profile policy. Default: `Todo`. For a private operator profile, Backlog is human parking/planning and is not dispatched.
4. Let CQ pick it on a scheduler tick.
5. Improve CQ itself whenever the workflow is painful or unclear.

Small conversational help can stay in chat. Durable or risky work should go through the queue.

## Issue quality bar

Every CQ-ready issue should answer:

- What outcome should change?
- Why does this matter?
- What is explicitly in scope?
- What is out of scope?
- How will completion be validated?
- Which agent/mode should handle it?
- Does any external action require human approval?

If an issue cannot answer those, route it to `ceo` or `cto` first for shaping.
