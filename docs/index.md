---
layout: home

hero:
  name: ClawQueue
  text: Local GitHub issue dispatch for operator-controlled AI agents
  tagline: Keep the contract in GitHub. Run the workers locally.
  image:
    src: /brand/png/clawqueue-mascot-only.png
    alt: ClawQueue mascot
  actions:
    - theme: brand
      text: Get Started
      link: /start/getting-started
    - theme: alt
      text: View GitHub
      link: https://github.com/ClawQueue/ClawQueue
    - theme: alt
      text: Read the docs
      link: /guide/operator-workflow


signals:
  - Local-first
  - GitHub-native
  - Powered by OpenClaw
  - Markdown-configurable
  - PR-reviewable

homepage:
  lede: >-
    ClawQueue keeps GitHub Issues and Projects as the durable work contract, then uses a local scheduler to pick eligible work, launch the right agent mode, and report results back to the issue.
  relationship: >-
    OpenClaw supplies the context-rich assistant layer: a human can ask the OpenClaw main agent for help in plain language, and OpenClaw can use project context to turn that rough prompt into a full GitHub issue. With the default `openclaw` backend, it can also run the specialist agents CQ dispatches.
  proof:
    - title: GitHub holds the contract
      details: Issues, labels, projects, comments, branches, PRs.
    - title: OpenClaw shapes the issue
      details: Rough operator prompts become scoped GitHub work with project context.
    - title: Your machine runs the workers
      details: OpenClaw, Claude Code, Codex, or other local runners.
    - title: Humans review the work
      details: Output returns as comments, artifacts, and PR-ready changes.
  how:
    title: Prompt-to-issue-to-agent work — without losing the thread
    description: >-
      OpenClaw can turn rough operator intent into a scoped GitHub issue, then CQ schedules one eligible issue, runs a configured local backend, and writes the result back where humans can audit it.
    steps:
      - title: Human Prompt
        details: Start with a rough operator prompt, question, or desired outcome.
      - title: OpenClaw Main Agent
        details: OpenClaw uses repo/profile context to shape the request.
      - title: Full GitHub Issue
        details: The prompt becomes a scoped issue with the details CQ needs.
      - title: CQ Scheduler
        details: CQ checks status, locks, attempts and policy.
      - title: OpenClaw / Local Runner
        details: CQ launches an OpenClaw specialist agent or another configured backend.
      - title: Comment / PR
        details: Result returns to the issue, ready to review.

features:
  - title: Durable work contract
    details: Issues, labels, projects, comments, branches, and PRs stay visible in GitHub instead of disappearing into a hidden runtime.
  - title: Local scheduler
    details: Your machine picks eligible issues, applies policy, and launches the configured runner — usually OpenClaw for full agent context, or direct CLI backends when configured.
  - title: Label-to-agent routing
    details: Turn labels into modes like docs, review, implementation, research, and project-specific operator flows.
  - title: Reviewable output
    details: Results return as comments, artifacts, branch links, and PR-ready changes a human can inspect.
  - title: Operator controlled
    details: Secrets stay local. Policy stays editable. Human review stays in the loop.
  - title: Small on purpose
    details: ClawQueue is a lightweight dispatch layer, not a bloated hosted workflow suite.
---

<div class="cq-home">

<div class="cq-signal-row" aria-label="trust bullets">
  <span>Local-first</span>
  <span>GitHub-native</span>
  <span>Powered by OpenClaw</span>
  <span>Markdown-configurable</span>
  <span>PR-reviewable</span>
</div>

<div class="cq-mascot-cards">
  <div class="cq-floating-card issue">issue #128</div>
  <div class="cq-floating-card label">label: agent:fix</div>
  <div class="cq-floating-card mode">mode: code-review</div>
  <div class="cq-floating-card runner">runner: local</div>
  <div class="cq-floating-card status">status: PR opened</div>
</div>

## GitHub is the durable work contract. Your machine runs the workers.

ClawQueue keeps source-of-truth work in GitHub Issues and Projects, then uses a local scheduler to pick eligible work, resolve labels into the right mode, launch the configured runner, and report the result back to the issue.

OpenClaw supplies the context-rich assistant layer: a human can ask the OpenClaw main agent for help in plain language, and OpenClaw can use project context to turn that rough prompt into a full GitHub issue. With the default `openclaw` backend, it can also run the specialist agents CQ dispatches.

<div class="cq-grid cq-what-grid">
  <div class="cq-card soft">
    <h3>Durable work contract</h3>
    <p>Keep task state in GitHub Issues and Projects, not in a mystery agent database or one chat thread nobody can audit later.</p>
  </div>
  <div class="cq-card soft">
    <h3>Local scheduler</h3>
    <p>CQ checks locks, limits, retries, branch state, and board status before it launches work on your own machine.</p>
  </div>
  <div class="cq-card soft">
    <h3>Label-to-agent routing</h3>
    <p>Map labels into modes like docs, review, implementation, research, or profile-specific workflows without hardcoding a giant orchestration stack.</p>
  </div>
  <div class="cq-card soft">
    <h3>Results back to GitHub</h3>
    <p>Agent output returns as comments, artifacts, branches, and PR links a human can review instead of trusting vibes.</p>
  </div>
</div>

## How it works

<div class="cq-card workflow-card">
  <div class="cq-flow">
    <span>Human Prompt</span>
    <b>→</b>
    <span>OpenClaw Main Agent</span>
    <b>→</b>
    <span>Full GitHub Issue</span>
    <b>→</b>
    <span>CQ Scheduler</span>
    <b>→</b>
    <span>Mode + Policy</span>
    <b>→</b>
    <span>OpenClaw / Local Runner</span>
    <b>→</b>
    <span>Worklog / PR / Comment</span>
  </div>
</div>

<div class="cq-steps">
  <div><strong>1. Human asks OpenClaw</strong><br/>Start with a rough operator prompt, question, or desired outcome.</div>
  <div><strong>2. OpenClaw creates the issue</strong><br/>The main agent uses repo/profile context to turn the prompt into a scoped GitHub issue with the details CQ needs.</div>
  <div><strong>3. Labels define intent</strong><br/>Labels map work to modes and safety policies.</div>
  <div><strong>4. CQ picks eligible work</strong><br/>Scheduler checks status, locks, attempts, and policy.</div>
  <div><strong>5. OpenClaw or another runner executes locally</strong><br/>CQ usually launches an OpenClaw specialist agent; direct Codex or Claude Code runners can be configured when that is the approved path.</div>
  <div><strong>6. Results return to GitHub</strong><br/>Comments, artifacts, branches, PR links, and next steps are written back to the issue.</div>
</div>

## Built for your own projects and external contributions

<div class="cq-grid cq-two-up">
  <div class="cq-card project-card">
    <h3>Operate your own project</h3>
    <p>Run CQ against your own repos, boards, profiles, and worklog. Keep strategy, implementation, review, and ops in one GitHub-native loop.</p>
  </div>
  <div class="cq-card dark fork-card">
    <h3>Contribute through a fork</h3>
    <p>Use the same issue-driven flow for external repos: shape work into issues on your fork, dispatch locally, then open a clean upstream PR after review.</p>
  </div>
</div>

## Why local-first

<div class="cq-grid cq-why-grid">
  <div class="cq-card mini"><h3>Private by default</h3><p>Secrets and runtime context stay on your machine.</p></div>
  <div class="cq-card mini"><h3>No vendor lock-in</h3><p>Swap runners without losing the task contract.</p></div>
  <div class="cq-card mini"><h3>Inspectable policy</h3><p>Routing and behavior live in markdown/config you can patch fast.</p></div>
  <div class="cq-card mini"><h3>Reviewable output</h3><p>The final state still lives in GitHub where humans can judge it.</p></div>
</div>

## Minimal config shape

```yaml
projects:
  - repo: your-org/your-repo
    dispatch_statuses: [Todo]
routing:
  agent_roles:
    cto: cto
    cmo: cmo
    reviewer: reviewer
review:
  default_level: standard
  levels: [standard, extra]
artifacts:
  backend: local
  path: .clawqueue/boards
  commit: false
```

For `cq:change` issues, the chief-of-staff intake step should set `review_level: standard | extra`. Use `extra` for risky, broad, public-facing, security-sensitive, or hard-to-verify changes; reviewers clear the item with `extra_review_required: false` or keep it open with `extra_review_required: true`.

## Use cases

<div class="cq-grid cq-use-cases">
  <div class="cq-card mini"><h3>Personal repo autopilot</h3><p>Use GitHub issues as a real queue instead of a graveyard.</p></div>
  <div class="cq-card mini"><h3>Startup engineering queue</h3><p>Route specs, fixes, docs, and reviews through one operator-controlled loop.</p></div>
  <div class="cq-card mini"><h3>Open-source contribution assistant</h3><p>Work through your fork and ship cleaner upstream PRs.</p></div>
  <div class="cq-card mini"><h3>Maintenance backlog sweeper</h3><p>Let boring but reviewable work move without losing visibility.</p></div>
  <div class="cq-card mini"><h3>Multi-agent workbench</h3><p>Use labels and profiles to coordinate specialist roles without giant tooling overhead.</p></div>
</div>

## Small by design. GitHub-native by default.

<div class="cq-grid cq-compare">
  <div class="cq-card soft">
    <h3>ClawQueue is</h3>
    <ul>
      <li>a local GitHub issue dispatcher</li>
      <li>a way to turn labels into agent modes</li>
      <li>a reviewable workflow for human-agent work</li>
      <li>a small layer you can inspect and modify</li>
    </ul>
  </div>
  <div class="cq-card soft">
    <h3>ClawQueue is not</h3>
    <ul>
      <li>a hosted PM suite</li>
      <li>a magical autonomous company in a box</li>
      <li>a secure multi-tenant executor</li>
      <li>a replacement for human review</li>
    </ul>
  </div>
</div>

<div class="cq-final-cta">
  <h2>Put your GitHub issues to work. Locally.</h2>
  <p>Start with the docs, wire up one board, and let CQ pick one safe issue at a time.</p>
  <div class="actions">
    <a class="action brand" href="/ClawQueue/start/getting-started">Get Started</a>
    <a class="action alt" href="https://github.com/ClawQueue/ClawQueue">View GitHub</a>
  </div>
  <p class="cq-footer-line">ClawQueue — GitHub issues in, agent work out.</p>
</div>

</div>
