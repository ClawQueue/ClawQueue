#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import plistlib
import shlex
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Install/update a local ClawQueue launchd scheduler")
    parser.add_argument("--repo", default=str(Path.cwd()), help="Path to ClawQueue repo; default: current directory")
    parser.add_argument(
        "--policy",
        default="config/company_workflow_policy.md",
        help="Workflow policy path, relative to repo or absolute. Ignored when --profile is set.",
    )
    parser.add_argument(
        "--profile",
        default="",
        help="Profile name under profiles/ to run. Preferred for shared profiles because it also loads profile-local private config.",
    )
    parser.add_argument("--interval", type=int, default=300, help="Run interval in seconds; default: 300")
    parser.add_argument("--label", default="com.clawqueue.scheduler", help="launchd label")
    parser.add_argument("--wrapper-name", default="clawqueue-scheduler.sh", help="Wrapper script name shown by macOS Background Items")
    args = parser.parse_args()

    repo = Path(args.repo).expanduser().resolve()
    profile = args.profile.strip()
    policy = Path(args.policy).expanduser()
    if not profile:
        if not policy.is_absolute():
            policy = repo / policy
        policy = policy.resolve()

    if not repo.exists():
        print(f"error: repo not found: {repo}", file=sys.stderr)
        return 1
    if profile and not (repo / "profiles" / profile).exists():
        print(f"error: profile not found: {repo / 'profiles' / profile}", file=sys.stderr)
        return 1
    if not profile and not policy.exists():
        print(f"error: policy not found: {policy}", file=sys.stderr)
        return 1

    service_env = Path.home() / ".openclaw" / "service-env"
    logs_dir = Path.home() / ".openclaw" / "tmp" / "clawqueue"
    state_root = logs_dir
    profile_state_dir = state_root / args.label.replace("/", "-")
    launch_agents = Path.home() / "Library" / "LaunchAgents"
    wrapper_path = service_env / args.wrapper_name
    plist_path = launch_agents / f"{args.label}.plist"

    service_env.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    profile_state_dir.mkdir(parents=True, exist_ok=True)
    launch_agents.mkdir(parents=True, exist_ok=True)

    if profile:
        command = f"exec /usr/bin/python3 scripts/scheduler.py --profile {shlex.quote(profile)}\n"
        selector = f"Profile: {profile}"
    else:
        command = "exec /usr/bin/python3 scripts/scheduler.py\n"
        selector = f"Policy: {policy}"
    wrapper_path.write_text(
        "#!/bin/bash\n"
        "set -euo pipefail\n"
        "export PATH=\"/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin\"\n"
        + ("" if profile else f"export CLAWQUEUE_POLICY_FILE=\"{policy}\"\n")
        + f"export CLAWQUEUE_STATE_DIR=\"{profile_state_dir}\"\n"
        + f"export CLAWQUEUE_SHARED_STATE_ROOT=\"{state_root}\"\n"
        + f"cd \"{repo}\"\n"
        + command
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
    print(selector)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
