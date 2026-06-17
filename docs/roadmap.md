---
type: Roadmap
title: Roadmap
description: Product direction, near-term themes, and features.
tags: [roadmap, direction, features]
timestamp: 2026-06-17T16:28:00Z
---

# Roadmap

ClawQueue v0.1.0 starts intentionally small and clean.

The public roadmap should live as GitHub issues and project items, not as a stale
promise document. This page records the product direction without pretending the
future is more certain than it is.

## Direction

- Keep GitHub as the durable work contract.
- Keep execution local and operator-controlled.
- Keep policy inspectable in markdown/config.
- Keep outputs reviewable through comments, artifacts, branches, and PRs.
- Keep the core small enough that one operator can understand it.

## Near-term themes

- Safer public onboarding
- Cleaner docs and examples
- GitHub Pages landing page
- Better profile/worklog separation
- Stronger diagnostics for misconfigured agents, projects, and labels

### Pre-Flight Deep Research Mode
To combat the "garbage-in, garbage-out" problem of vague or ambiguous issue specifications, we are introducing a dedicated, iterative pre-flight research workflow. When a ticket is created with raw human intent, a specialized research worker runs a multi-step context collection loop—crawling local workspace files, project documentation, and external resources—to compile a comprehensive technical specification or RFC. This specification is posted back to the GitHub issue for human review, ensuring clear requirements are locked in *before* code execution agents are dispatched.

### Multi-Model Compare & A/B Review
Evaluating system prompt tweaks, persona adjustments, or competing model capabilities (e.g., Azure AI Foundry vs. Anthropic) is difficult in isolated local environments. We are adding an automated A/B-testing framework directly into the CQ scheduler. By labeling an issue for comparison, the control loop dispatches the task to multiple candidate agents or model backends in parallel. The resulting code and artifact variations are submitted as competing pull request drafts or structured side-by-side comments, allowing the operator to perform objective, blind reviews directly within the GitHub native interface.

Concrete work should be tracked as issues.
