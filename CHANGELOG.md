# Changelog

## Unreleased

### Added

- Added `COMPANY_CHARTER.md` as a generic company-profile charter template with mission, vision, north star, work taxonomy, and human approval boundaries.
- Added `ROADMAP.md` with the company-agent foundation milestone before deeper orchestration improvements.
- Added a GitHub issue template for structured human/agent tasks.
- Restored `researcher` as a separate evidence/research persona/mode and kept CMO focused on growth, demand, sales, marketing, social, and partnerships.
- Removed the legacy scheduler pickup label requirement; Todo board status and normal eligibility checks now decide candidates.
- Added append-only JSONL decision logging and `scripts/status.py` for operator visibility.

### Changed

- Rescoped agent identities, souls, and modes from a narrow domain-specific frame to a broader generic company-agent framework covering product, engineering, research, sales, marketing, social, partnerships, ops, and review.
- Refactored the scheduler into `clawqueue/` modules:
  - `config.py` for repo policy, private config, and environment overrides
  - `tracker.py` for GitHub issue and ProjectV2 access
  - `dispatcher.py` for task selection, locking, sweeping, quotas, and dispatch
  - `runner.py` for prompt construction and agent process launch
  - `activity.py` and `notifications.py` for local activity gates and optional Telegram asks
- Renamed the executable entry point to `scripts/scheduler.py`.
- Renamed the workflow policy to `config/company_workflow_policy.md`.
- Standardized scheduler retry terminology around attempt counts.
- Replaced comment substring completion detection with a structured completion sentinel.
- Moved private deployment details out of tracked code and into environment variables or ignored private config.
- Added shareable policy and private-config example files under `config/`.
- Added `.gitignore` entries for Python caches, local runtime state, env files, and private config.

### Security

- Removed hardcoded bot credentials, chat IDs, GitHub ProjectV2 node IDs, status option IDs, and personal assignee values from tracked scheduler code.
- Documented the trusted-environment boundary: this project shells out to local CLIs and is not secure multi-tenant infrastructure.
