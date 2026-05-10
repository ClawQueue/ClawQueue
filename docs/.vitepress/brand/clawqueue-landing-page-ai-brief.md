# ClawQueue Landing Page AI Brief

Use this as the full prompt/spec for an AI website builder, designer, or frontend coding agent.

---

## Project

**Name:** ClawQueue  
**Short name:** CQ  
**Product category:** Local-first GitHub issue dispatcher for one operator and their AI agents.

**Core idea:**  
ClawQueue keeps the durable work contract in GitHub Issues and GitHub Projects, while a local scheduler on the operator’s machine picks eligible work, resolves issue labels into agent modes, launches the configured runner, and reports results back to the issue.

**Positioning:**  
A small, local-first dispatch layer for people who use GitHub as their control plane and want AI agents to work through issue-driven, reviewable PR workflows.

---

## Selected Logo Direction

Use `selected-logo-reference.png` as the visual reference.

### Logo description

The logo is a friendly but capable robotic lobster/claw mascot forming a “C” shape around a queue/issue icon. The shell is vivid lobster orange/red, but the internal mechanics, claw shadows, and “Queue” wordmark are dark navy, creating a “night ops” feel. Cyan/blue highlights represent signal, operator control, agent activity, and GitHub issue flow.

### Brand personality

- Local-first
- Technical but approachable
- Operator-controlled
- Agentic, but not chaotic
- Small, reliable, practical
- Night-ops / command-center energy
- Playful enough to be memorable, but not childish

### Visual vibe

Think: “cute ops mascot meets reliable devtool.”  
Not enterprise boring. Not toy-like. More like a sharp indie devtool with a strong mascot.

---

## Color System

Use the selected logo palette.

```css
:root {
  --cq-lobster-orange: #FF4A12;
  --cq-lobster-red: #E21B0C;
  --cq-deep-navy: #07162B;
  --cq-ink-navy: #0B1E3A;
  --cq-cyan: #12BFF5;
  --cq-signal-blue: #158BFF;
  --cq-ice-blue: #EAF7FF;
  --cq-soft-bg: #F7FAFC;
  --cq-white: #FFFFFF;
  --cq-muted: #64748B;
  --cq-border: #DDE7F0;
}
```

### Primary palette

- Lobster Orange: `#FF4A12`
- Lobster Red: `#E21B0C`
- Deep Navy: `#07162B`
- Cyan: `#12BFF5`
- Signal Blue: `#158BFF`
- White: `#FFFFFF`

### Recommended gradients

```css
--cq-gradient-claw: linear-gradient(135deg, #FF5A18 0%, #E21B0C 100%);
--cq-gradient-night: linear-gradient(135deg, #07162B 0%, #0B1E3A 55%, #102A4C 100%);
--cq-gradient-signal: linear-gradient(135deg, #12BFF5 0%, #158BFF 100%);
```

### Usage

- Use orange/red for the “Claw” side: primary CTAs, hero accents, key highlights.
- Use navy for structure, text, header, footer, dark sections, code blocks.
- Use cyan/blue sparingly for signals, agent status, queues, diagrams, hover states, and secondary CTAs.
- Keep backgrounds mostly white or very pale blue, with one strong dark “night ops” section.

---

## Typography

Use clean, modern, rounded devtool typography.

Recommended:
- Headings: **Space Grotesk**, **Nunito Sans**, or **Inter Tight**
- Body: **Inter**
- Code/config examples: **JetBrains Mono** or **Geist Mono**

Suggested CSS:

```css
body {
  font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  color: var(--cq-deep-navy);
}

h1, h2, h3 {
  font-family: "Space Grotesk", Inter, system-ui, sans-serif;
  letter-spacing: -0.04em;
}
```

---

## Landing Page Goal

Convert technical visitors into:
1. GitHub stars
2. Documentation readers
3. Early adopters who install/run CQ locally
4. Contributors who understand the issue-driven workflow

Primary CTA:
- **Get Started**

Secondary CTA:
- **View GitHub**
- **Read the Docs**

---

## Hero Section

### Headline options

Use one of these:

1. **Local GitHub issue dispatch for operator-controlled AI agents**
2. **Turn GitHub Issues into a local AI agent queue**
3. **Run your agents locally. Keep the contract in GitHub.**
4. **A tiny control plane for issue-driven agent work**

Recommended final headline:

> **Local GitHub issue dispatch for operator-controlled AI agents**

### Subheadline

> ClawQueue keeps GitHub Issues and Projects as the durable work contract, then uses a local scheduler to pick eligible work, launch the right agent mode, and report results back to the issue.

### CTA row

- Primary button: **Get Started**
- Secondary button: **View GitHub**
- Tertiary text link: **Read the docs**

### Trust bullets below CTA

- Local-first
- GitHub-native
- Markdown-configurable
- PR-reviewable
- Built for one operator + their agents

### Hero visual

Use the selected mascot/logo on the right.  
On the left, use headline/copy.  
Add small floating cards around the mascot showing:

- `issue #128`
- `label: agent:fix`
- `mode: code-review`
- `runner: claude-code`
- `status: PR opened`

---

## Site Navigation

Header nav:

- How it works
- Use cases
- Config
- Workflow
- Docs
- GitHub

Header buttons:

- Secondary: GitHub
- Primary: Get Started

---

## Page Structure

### 1. Hero

Large logo/mascot, headline, subheadline, CTAs, trust bullets.

---

### 2. What ClawQueue Does

Section heading:

> **GitHub is the control plane. Your machine runs the workers.**

Cards:

#### Durable work contract
Keep source-of-truth work in GitHub Issues and Projects, not a hidden agent database.

#### Local scheduler
CQ watches eligible issues, applies policy, picks the next safe unit of work, and launches the configured runner.

#### Label-to-agent routing
Turn labels into modes like `bugfix`, `test`, `docs`, `review`, `refactor`, or project-specific agent profiles.

#### Results back to GitHub
Agent output, logs, status, branch links, and PRs are reported back to the original issue.

---

### 3. How It Works

Use a horizontal or vertical flow diagram.

Flow:

1. **Issue created**
   - A task lands in GitHub Issues or Projects.
2. **Labels define intent**
   - Labels map work to agent modes and safety policies.
3. **CQ picks eligible work**
   - Local scheduler checks priority, locks, branch state, dependencies, and limits.
4. **Runner executes locally**
   - CQ launches the configured CLI/agent runner with the right context.
5. **Results return to GitHub**
   - Worklog, comments, PR links, and next steps are written back to the issue.

Suggested diagram labels:

```text
GitHub Issue → CQ Scheduler → Agent Mode → Local Runner → Worklog / PR / Comment
```

---

### 4. Two Practical Modes

Section heading:

> **Built for your own projects and external contributions**

#### Mode 1: Operate your own project

Copy:

> Use your own CQ profile, project board, agents, labels, and worklog. CQ becomes a lightweight local dispatcher for your company or personal project.

Bullets:

- Your labels
- Your runners
- Your branch policy
- Your review flow
- Your local machine

#### Mode 2: Contribute through a fork

Copy:

> For external or open-source repositories, CQ can build a project-specific profile from the upstream README, docs, and contribution rules, then route issue-driven agent work into reviewed PRs from your fork.

Bullets:

- Read upstream contribution rules
- Create a project-specific CQ profile
- Work from your fork
- Submit reviewed PRs
- Keep upstream expectations visible

---

### 5. Why Local-First

Section heading:

> **Agents should not need a SaaS control tower to work through GitHub.**

Cards:

#### Private by default
Your machine runs the workers. You decide what context is exposed to which runner.

#### No vendor lock-in
Use GitHub, markdown, config files, and the runners you already trust.

#### Inspectable policy
Routing rules, labels, modes, and contribution policies stay editable in markdown/config.

#### Reviewable output
Work lands in GitHub as comments, branches, logs, and PRs — not mystery automation.

---

### 6. Example Config / Markdown Policy

Show a clean code block. Example:

```yaml
profiles:
  default:
    repo: acme/project
    board: engineering
    max_parallel: 2

labels:
  agent:bugfix:
    mode: bugfix
    runner: claude-code
    priority: normal
    requires_review: true

  agent:docs:
    mode: docs
    runner: codex
    priority: low
    requires_review: false

policy:
  branch_prefix: cq/
  open_pr: true
  comment_worklog: true
  require_clean_tree: true
```

Caption:

> Policy is boring on purpose: editable, reviewable, and close to the repo.

---

### 7. Use Cases

Cards:

#### Personal repo autopilot
Queue small issues and let agents pick them up while you stay in control.

#### Startup engineering queue
Use GitHub Projects as a lightweight local dispatch board without adding a new SaaS workflow.

#### Open-source contribution assistant
Translate upstream contribution rules into a safe project profile and route work through PRs.

#### Maintenance backlog sweeper
Handle docs, tests, refactors, and bugfixes with labels and repeatable agent modes.

#### Multi-agent workbench
Try different runners or modes while keeping GitHub as the shared audit log.

---

### 8. “Not Another Agent Platform” Section

Use a direct comparison.

Heading:

> **Small by design. GitHub-native by default.**

Table:

| ClawQueue is | ClawQueue is not |
|---|---|
| A local scheduler | A hosted agent platform |
| A GitHub issue dispatcher | A replacement for GitHub Projects |
| Markdown/config driven | A black-box automation layer |
| Operator-controlled | Fully autonomous chaos |
| Runner-agnostic | Tied to one model/provider |

---

### 9. CTA Section

Dark navy background with orange mascot glow.

Headline:

> **Put your GitHub issues to work. Locally.**

Copy:

> Start with one repo, a few labels, and one runner. Keep the workflow visible in GitHub and the execution under your control.

Buttons:

- **Get Started**
- **View GitHub**

---

### 10. Footer

Footer columns:

Product:
- How it works
- Config
- Use cases
- Docs

Project:
- GitHub
- Issues
- Releases
- Contributing

Brand line:

> ClawQueue — GitHub issues in, agent work out.

---

## Suggested Landing Page Copy

### Meta title

ClawQueue — Local GitHub Issue Dispatch for AI Agents

### Meta description

ClawQueue is a local-first GitHub issue dispatcher that routes labeled issues to AI agent runners, tracks work in GitHub, and keeps operators in control.

### Open Graph title

ClawQueue: Local GitHub issue dispatch for operator-controlled AI agents

### Open Graph description

Use GitHub Issues as the control plane, run agents locally, and route work through reviewable PRs.

---

## Visual Design Instructions

### Layout

- Use a clean SaaS/devtool landing page layout.
- White or very light background for most sections.
- Dark “night ops” section near the bottom.
- Use rounded cards, soft shadows, and subtle gradient borders.
- Use blue/cyan status lights and small signal motifs.
- Avoid generic stock illustrations.

### Components

Create these reusable components:

- Header
- Hero
- FeatureCard
- WorkflowStep
- ModeCard
- UseCaseCard
- ConfigBlock
- CTASection
- Footer

### Micro-interactions

- Primary buttons slightly glow orange on hover.
- Secondary buttons use navy border and cyan hover.
- Workflow cards can gently animate in sequence.
- Mascot can have very subtle floating animation.
- Signal lines near antenna can pulse lightly.

Keep animations tasteful. This should feel reliable, not gimmicky.

---

## Website Builder / Coding Agent Prompt

Copy-paste this prompt into your AI website builder:

```text
Create a polished landing page for ClawQueue, a local-first GitHub issue dispatcher for one operator and their AI agents.

Use the attached selected-logo-reference.png as the core brand identity. The logo is a robotic lobster/claw mascot shaped like a C, with orange/red “claw” shell, dark navy mechanical/night-ops elements, cyan signal lights, and a queue/issue icon. Keep the page visually aligned with this: local-first, GitHub-native, operator-controlled, technical but approachable, night-ops devtool energy.

Product explanation:
ClawQueue keeps the durable work contract in GitHub Issues and GitHub Projects. A local scheduler picks eligible work, resolves issue labels into agent modes, launches the configured runner, and reports results back to the issue. It is intentionally small: GitHub is the control plane, the operator’s machine runs the workers, and policy stays in editable markdown/config.

The page should target developers, technical founders, maintainers, and people building with AI coding agents.

Use this primary headline:
“Local GitHub issue dispatch for operator-controlled AI agents”

Use this subheadline:
“ClawQueue keeps GitHub Issues and Projects as the durable work contract, then uses a local scheduler to pick eligible work, launch the right agent mode, and report results back to the issue.”

Primary CTA: Get Started
Secondary CTA: View GitHub
Also include: Read the docs

Use these colors:
- Lobster Orange #FF4A12
- Lobster Red #E21B0C
- Deep Navy #07162B
- Ink Navy #0B1E3A
- Cyan #12BFF5
- Signal Blue #158BFF
- Ice Blue #EAF7FF
- Soft BG #F7FAFC
- White #FFFFFF
- Muted #64748B
- Border #DDE7F0

Use fonts:
- Headings: Space Grotesk or Inter Tight
- Body: Inter
- Code: JetBrains Mono

Page sections:
1. Header with nav: How it works, Use cases, Config, Workflow, Docs, GitHub.
2. Hero with logo/mascot, headline, subheadline, CTA buttons, and trust bullets: Local-first, GitHub-native, Markdown-configurable, PR-reviewable, Built for one operator + their agents.
3. “GitHub is the control plane. Your machine runs the workers.” Feature cards:
   - Durable work contract
   - Local scheduler
   - Label-to-agent routing
   - Results back to GitHub
4. “How it works” workflow diagram:
   GitHub Issue → CQ Scheduler → Agent Mode → Local Runner → Worklog / PR / Comment
5. “Built for your own projects and external contributions” with two mode cards:
   - Operate your own project
   - Contribute through a fork
6. “Why local-first” section:
   - Private by default
   - No vendor lock-in
   - Inspectable policy
   - Reviewable output
7. Config example code block using YAML.
8. Use cases:
   - Personal repo autopilot
   - Startup engineering queue
   - Open-source contribution assistant
   - Maintenance backlog sweeper
   - Multi-agent workbench
9. Comparison section titled “Small by design. GitHub-native by default.” with a two-column “ClawQueue is / is not” table.
10. Final dark CTA section:
   “Put your GitHub issues to work. Locally.”
   Buttons: Get Started, View GitHub.
11. Footer with product/project links and line:
   “ClawQueue — GitHub issues in, agent work out.”

Style:
Clean devtool SaaS landing page. Mostly white/light backgrounds, with one dark navy night-ops section. Rounded cards, soft shadows, subtle cyan signal details, orange CTAs. Use the mascot/logo prominently. Avoid generic stock art. Make it feel like a serious indie developer tool with a memorable mascot.

If coding, create a responsive page. Use semantic HTML. Make sure mobile layout is excellent.
```

---

## Recommended Hero Mockup Layout

```text
[Header]
Logo left                                         Nav + CTA right

[Hero]
Left:
  Badge: Local-first • GitHub-native • Agent-ready
  H1
  Subheadline
  CTA buttons
  Trust bullets

Right:
  Large mascot/logo
  Floating cards:
    issue #128
    label: agent:bugfix
    mode: fix
    runner: local
    PR opened
```

---

## Tone of Voice

Plainspoken, technical, and practical.

Good phrases:
- “Keep the contract in GitHub.”
- “Run the workers locally.”
- “Route labels into agent modes.”
- “Operator-controlled by default.”
- “Reviewable PRs, not mystery automation.”
- “Small on purpose.”

Avoid:
- “Revolutionary”
- “10x your engineering team”
- “Autonomous AI employees”
- “Magic”
- “Enterprise-grade AI orchestration platform”

---

## Short Product Explanation

ClawQueue is a tiny local dispatcher for GitHub issue-driven agent work. GitHub stays the source of truth. Your machine runs the workers. Markdown/config decides which labels map to which agent modes. Results come back to GitHub as comments, logs, branches, and PRs.

---

## Final Landing Page Taglines

Use one of these:

- GitHub issues in. Agent work out.
- Keep the contract in GitHub. Run the workers locally.
- Local dispatch for issue-driven agent work.
- Small scheduler. Clear policy. Reviewable PRs.
- Operator-controlled agent work, routed through GitHub.

Recommended:

> **Keep the contract in GitHub. Run the workers locally.**
