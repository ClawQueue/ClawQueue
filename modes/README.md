# Modes - Cognitive Operating Modes

These files define the cognitive context injected into each agent when picking up a GitHub issue. The scheduler/dispatcher reads issue labels, selects the appropriate mode file, and prepends it to the task prompt.

Root modes are generic seed prompts. Company-specific mode prompts should live in `profiles/<company>/modes/` and be selected with `CLAWQUEUE_MODES_DIR` or profile-specific configuration.

## Label -> Agent -> Mode Routing

| Label | Agent | Model | Mode File | Purpose |
|-------|-------|-------|-----------|---------|
| `ceo` | `ceo` | gpt-5.5 (Codex) | `ceo.md` | Strategy, mission leverage, scope challenge |
| `cto` | `cto` | gpt-5.5 (Codex) | `cto.md` | Product/technical architecture, edge cases, tests, approval gates |
| `engineer` | `dev` | gpt-5.5 (Codex) | `engineer.md` | Scoped implementation across code, automation, docs, and drafts |
| `cmo` | `cmo` | gpt-5.5 (Codex) | `cmo.md` | Growth, demand, sales, marketing, social, partnerships, and customer evidence |
| `researcher` | `researcher` | gpt-5.5 (Codex) | `researcher.md` | Market, customer, technical, scientific, and evidence research |
| `reviewer` | `reviewer` | gpt-5.5 (Codex) | `reviewer.md` | Code, plan, claim, brand-risk, security, and approval-boundary review |

**Priority order when multiple labels are present:** `ceo > cto > reviewer > cmo > researcher > engineer`

`engineer` labels route to the `dev` agent. The current runner does not prepend an engineer mode prompt for `dev`/`engineer` tasks; the persona files carry that behavior.

## Work Taxonomy

Use these labels or issue-category notes to frame work:

- `strategy`
- `product`
- `engineering`
- `research`
- `sales`
- `marketing`
- `social`
- `partnerships`
- `ops`
- `review`

These categories describe the work. They do not replace routing labels unless the dispatcher is extended later.

## Human Approval Boundary

Agents are internal team assistants. External-facing work is draft-only until a human approves it.

Human approval is required before publishing, sending, pricing, promising, or committing anything related to public communications, outbound sales or partnerships, commercial terms, legal/financial/regulatory claims, official roadmap, product delivery, or official company authority.

## Local mode resolution

The scheduler resolves local mode prompts from `CLAWQUEUE_MODES_DIR` first and falls back to `CLAWQUEUE_MODES_BASE_URL/<mode>.md` if the file is missing locally.

## Editing modes

Edit the `.md` files in this directory for generic defaults. Edit profile mode files for company-specific behavior.
