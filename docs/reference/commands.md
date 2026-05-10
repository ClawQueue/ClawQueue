# Commands

ClawQueue is currently operated through Python scripts.

## Status

```bash
python3 scripts/status.py --no-queue
python3 scripts/status.py
```

## Scheduler

```bash
python3 scripts/scheduler.py
```

## Bootstrap project board

```bash
python3 scripts/bootstrap_project_board.py
```

## Install launchd scheduler on macOS

```bash
python3 scripts/install_launchd.py --repo "$HOME/ClawQueue" --policy config/company_workflow_policy.md
```
