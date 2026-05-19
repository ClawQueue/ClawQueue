#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import plistlib
import re
import shlex
import subprocess
import sys
from pathlib import Path


def label_slug(label: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", label.strip()).strip("-.")
    return slug or "scheduler"


def resolve_repo_path(repo: Path, value: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = repo / path
    return path.resolve()


def default_private_config(repo: Path, profile: str, policy: Path | None) -> Path:
    if profile:
        return repo / "profiles" / profile / "config" / "clawqueue.private.json"
    if policy:
        return policy.parent / "clawqueue.private.json"
    return repo / "config" / "clawqueue.private.json"


def shell_export(name: str, value: Path | str) -> str:
    return f"export {name}={shlex.quote(str(value))}\n"


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
    parser.add_argument(
        "--private-config",
        default="",
        help="Private config JSON path, relative to repo or absolute. Defaults to the active profile/policy config directory.",
    )
    parser.add_argument(
        "--state-dir",
        default="",
        help="Scheduler state dir. Default: ~/.openclaw/tmp/clawqueue/<sanitized-label>.",
    )
    parser.add_argument(
        "--log-dir",
        default="",
        help="Scheduler log dir. Default: ~/.local/share/clawqueue/<sanitized-label>.",
    )
    parser.add_argument("--interval", type=int, default=300, help="Run interval in seconds; default: 300")
    parser.add_argument("--label", default="com.clawqueue.scheduler", help="launchd label")
    parser.add_argument("--wrapper-name", default="clawqueue-scheduler.sh", help="Wrapper script name shown by macOS Background Items")
    args = parser.parse_args()

    repo = Path(args.repo).expanduser().resolve()
    profile = args.profile.strip()
    policy: Path | None = Path(args.policy).expanduser()
    if not profile:
        if not policy.is_absolute():
            policy = repo / policy
        policy = policy.resolve()
    else:
        policy = None

    if not repo.exists():
        print(f"error: repo not found: {repo}", file=sys.stderr)
        return 1
    if profile and not (repo / "profiles" / profile).exists():
        print(f"error: profile not found: {repo / 'profiles' / profile}", file=sys.stderr)
        return 1
    if policy and not policy.exists():
        print(f"error: policy not found: {policy}", file=sys.stderr)
        return 1

    private_config = (
        resolve_repo_path(repo, args.private_config)
        if args.private_config.strip()
        else default_private_config(repo, profile, policy)
    )
    if args.private_config.strip() and not private_config.exists():
        print(f"error: private config not found: {private_config}", file=sys.stderr)
        return 1

    safe_label = label_slug(args.label)
    service_env = Path.home() / ".openclaw" / "service-env"
    state_root = Path.home() / ".openclaw" / "tmp" / "clawqueue"
    state_dir = resolve_repo_path(repo, args.state_dir) if args.state_dir.strip() else state_root / safe_label
    shared_state_root = state_dir
    log_dir = (
        resolve_repo_path(repo, args.log_dir)
        if args.log_dir.strip()
        else Path.home() / ".local" / "share" / "clawqueue" / safe_label
    )
    launch_agents = Path.home() / "Library" / "LaunchAgents"
    wrapper_path = service_env / args.wrapper_name
    plist_path = launch_agents / f"{args.label}.plist"

    service_env.mkdir(parents=True, exist_ok=True)
    state_root.mkdir(parents=True, exist_ok=True)
    state_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
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
        + ("" if profile else shell_export("CLAWQUEUE_POLICY_FILE", policy or ""))
        + shell_export("CLAWQUEUE_PRIVATE_CONFIG_FILE", private_config)
        + shell_export("CLAWQUEUE_STATE_DIR", state_dir)
        + shell_export("CLAWQUEUE_LOG_DIR", log_dir)
        + shell_export("CLAWQUEUE_SHARED_STATE_ROOT", shared_state_root)
        + f"cd {shlex.quote(str(repo))}\n"
        + command
    )
    wrapper_path.chmod(0o700)

    stdout_log = log_dir / f"{safe_label}.stdout.log"
    stderr_log = log_dir / f"{safe_label}.stderr.log"

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
    print(f"State: {state_dir}")
    print(f"Logs: {log_dir}")
    print(f"Private config: {private_config}")
    print(selector)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
