#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import plistlib
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Install/update a local ClawQueue launchd scheduler")
    parser.add_argument("--repo", default=str(Path.cwd()), help="Path to ClawQueue repo; default: current directory")
    parser.add_argument("--policy", default="config/company_workflow_policy.md", help="Workflow policy path, relative to repo or absolute")
    parser.add_argument("--interval", type=int, default=300, help="Run interval in seconds; default: 300")
    parser.add_argument("--label", default="com.clawqueue.scheduler", help="launchd label")
    parser.add_argument("--wrapper-name", default="clawqueue-scheduler.sh", help="Wrapper script name shown by macOS Background Items")
    args = parser.parse_args()

    repo = Path(args.repo).expanduser().resolve()
    policy = Path(args.policy).expanduser()
    if not policy.is_absolute():
        policy = repo / policy
    policy = policy.resolve()

    if not repo.exists():
        print(f"error: repo not found: {repo}", file=sys.stderr)
        return 1
    if not policy.exists():
        print(f"error: policy not found: {policy}", file=sys.stderr)
        return 1

    service_env = Path.home() / ".openclaw" / "service-env"
    logs_dir = Path.home() / ".openclaw" / "tmp" / "clawqueue"
    launch_agents = Path.home() / "Library" / "LaunchAgents"
    wrapper_path = service_env / args.wrapper_name
    plist_path = launch_agents / f"{args.label}.plist"

    service_env.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    launch_agents.mkdir(parents=True, exist_ok=True)

    wrapper_path.write_text(
        "#!/bin/bash\n"
        "set -euo pipefail\n"
        "export PATH=\"/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin\"\n"
        f"export CLAWQUEUE_POLICY_FILE=\"{policy}\"\n"
        f"cd \"{repo}\"\n"
        "exec /usr/bin/python3 scripts/scheduler.py\n"
    )
    wrapper_path.chmod(0o700)

    log_safe_label = args.label.replace("/", "-")
    stdout_log = logs_dir / f"{log_safe_label}.stdout.log"
    stderr_log = logs_dir / f"{log_safe_label}.stderr.log"

    plist = {
        "Label": args.label,
        "ProgramArguments": [str(wrapper_path)],
        "WorkingDirectory": str(repo),
        "StartInterval": int(args.interval),
        "RunAtLoad": True,
        "StandardOutPath": str(stdout_log),
        "StandardErrorPath": str(stderr_log),
        "ProcessType": "Background",
    }
    with plist_path.open("wb") as f:
        plistlib.dump(plist, f, sort_keys=False)

    uid = str(os.getuid())
    subprocess.run(["plutil", "-lint", str(plist_path)], check=True)
    subprocess.run(["launchctl", "bootout", f"gui/{uid}", str(plist_path)], check=False)
    subprocess.run(["launchctl", "bootstrap", f"gui/{uid}", str(plist_path)], check=True)
    subprocess.run(["launchctl", "kickstart", "-k", f"gui/{uid}/{args.label}"], check=True)

    print(f"Installed: {args.label}")
    print(f"Plist: {plist_path}")
    print(f"Wrapper: {wrapper_path}")
    print(f"Logs: {logs_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
