# ClawQueue Product Context

This file gives CQ agents a compact product map for ClawQueue itself.

## Product in one page

ClawQueue is a **local GitHub issue dispatcher for one operator and their agents**.

It keeps the durable work contract in GitHub Issues/Projects while a local scheduler:

- scans configured repos/projects
- resolves labels into modes and agents
- launches the configured runner (`openclaw`, `claude`, or `codex`)
- writes results back to the issue
- preserves review history outside the runtime

## Strategic model

- **Adopt** — make CQ easy to understand and try from the README and operator docs.
- **Trust** — make behavior visible, deterministic enough, and easy to diagnose.
- **Operate** — keep local execution, config, and profile workflows simple enough for one operator to own.
- **Extend** — support profile-specific agents, routing, and worklog patterns without forking core CQ.

## Core system areas

### Scheduler and dispatcher

Eligibility rules, board/status policy, dispatch loop, attempt limits, cooldowns, activity gates, stale-work reconciliation, and failure handling.

### Runner layer

Prompt construction, mode injection, artifact expectations, backend launching, completion contract handling, and worker logs.

### Config and profiles

Tracked policy, private overrides, selected profile loading, mode-to-agent routing, repo/project mapping, and worklog/artifact configuration.

### Tracker and GitHub integration

Issue reads, comments, labels, assignment, board status changes, dependency interpretation, and visible queue state.

### Docs and onboarding

README, operator workflow docs, example profile, profile conventions, worklog conventions, and launch-ready explanations.

### Self-operation

CQ using its own workflow patterns: internal profile, internal worklog repo, durable artifacts, and issue-driven improvements.

## Source-of-truth model

For CQ itself:

- **GitHub Issues** — durable task contracts and review history
- **GitHub Projects** — queue visibility and human review lane
- **Profile docs** — mission, role instructions, routing rules, and operating policy
- **Worklog repo** — durable generated artifacts when needed
- **Human approval** — required for public positioning, official claims, and external announcements

## Approval boundary

Agents may draft and implement, but humans approve before anything is publicly announced, promised, priced, licensed, or represented as official project policy.

This is especially strict for:

- README/website claims about stability, safety, or support
- launch messaging and social announcements
- roadmap promises or compatibility claims
- commercial/licensing language
- statements that imply an official ClawQueue guarantee
