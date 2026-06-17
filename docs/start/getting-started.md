---
type: Quickstart
title: Getting Started
description: Learn how to install and configure ClawQueue for the first time.
tags: [setup, installation, requirements]
timestamp: 2026-06-17T16:28:00Z
---

# Getting started

ClawQueue is early. For v0.1.0, treat it as a trusted local tool for one
operator running against GitHub repositories and projects they control.

## Requirements

- Python 3.11+
- GitHub CLI (`gh`) authenticated with access to your issue repo/project
- A local runner you explicitly approve, such as OpenClaw, Claude Code, or Codex
- A GitHub issue repo and, optionally, a GitHub Project board

## Install from source

```bash
git clone https://github.com/ClawQueue/ClawQueue.git
cd ClawQueue
python3 -m pytest -q
```

## Configure a private deployment

Copy the example config and fill in deployment-specific values outside public
git history:

```bash
cp config/clawqueue.private.example.json config/clawqueue.private.json
$EDITOR config/clawqueue.private.json
```

Private values include repository names, ProjectV2 IDs, status option IDs,
assignees, bot tokens, chat IDs, and local runner names.

## Run one manual scheduler tick

```bash
python3 scripts/status.py --no-queue
python3 scripts/scheduler.py
```

Validate that one eligible issue moves through the expected states before adding
a periodic scheduler.

## Next steps

- Learn the [operator workflow](/guide/operator-workflow.md)
- Set up [configuration](/guide/configuration.md)
- Decide where [artifacts](/guide/artifacts.md) should live
