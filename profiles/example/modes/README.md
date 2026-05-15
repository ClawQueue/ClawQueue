# Modes - Cognitive Operating Modes

These files define the cognitive context injected into each agent when picking up a GitHub issue. The scheduler/dispatcher reads the issue labels, selects the appropriate mode file, and prepends it to the task prompt.

All modes inherit `COMPANY_CHARTER.md`. They support ExampleCo SaaS work across product, engineering, data/research, sales, marketing, social, partnerships, operations, and review.

## Label -> Agent -> Mode Routing

| Label | Agent | Model | Mode File | Purpose |
|-------|-------|-------|-----------|---------|
| `ceo` | `ceo` | gpt-5.5 (Codex) | `ceo.md` | Strategy, mission leverage, product-led growth, scope challenge |
| `cto` | `cto` | gpt-5.5 (Codex) | `cto.md` | Product/technical architecture, edge cases, tests, approval gates |
| `engineer` | `dev` | gpt-5.5 (Codex) | `engineer.md` | Scoped implementation across code, automation, docs, and drafts |
| `cmo` | `cmo` | gpt-5.5 (Codex) | `cmo.md` | Growth, demand, sales, marketing, social, partnerships, and customer evidence |
| `researcher` | `researcher` | gpt-5.5 (Codex) | `researcher.md` | PhD SaaS product research, weather science, experiment verification, product/data quality |
| `reviewer` | `reviewer` | gpt-5.5 (Codex) | `reviewer.md` | Code, plan, claim, brand-risk, security, approval-boundary, and Codex-review gate for code deliverables |

**Priority order when multiple labels are present:** `ceo > cto > reviewer > cmo > researcher > engineer`

`engineer` labels route to the `dev` agent. The current runner does not prepend an engineer mode prompt for `dev`/`engineer` tasks; the persona files carry that behavior.

## Work Taxonomy

Use these labels or issue-category notes to frame work:

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

These categories describe the work. They do not replace the existing routing labels unless the dispatcher is extended later.

## Human Approval Boundary

Agents are internal team assistants. External-facing work is draft-only until a human approves it.

Human approval is required before publishing, sending, pricing, promising, or committing anything related to public communications, outbound sales or partnerships, commercial terms, legal/financial/regulatory/token claims, official roadmap, product delivery, or official ExampleCo authority.

## Agents

OpenClaw agents are typically configured under `$OPENCLAW_HOME/agents/`:

- **`ceo`** - strategy and mission leverage
- **`cto`** - product and technical architecture
- **`dev`** - implementation
- **`cmo`** - growth, demand, narrative, customer evidence, sales/marketing/social
- **`researcher`** - SaaS product research, weather science, experiment verification, product/data quality
- **`reviewer`** - risk, correctness, claims, approval boundaries, and advisory Codex review for code deliverables

## Local mode resolution

The scheduler resolves local mode prompts from `CLAWQUEUE_MODES_DIR` first and falls back to `CLAWQUEUE_MODES_BASE_URL/<mode>.md` if the file is missing locally.

## Editing modes

Edit the `.md` files in this directory. Changes are picked up on the next scheduler run. No code changes are needed.
