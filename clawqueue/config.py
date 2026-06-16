from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_POLICY_FILE = REPO_ROOT / "config" / "company_workflow_policy.md"
DEFAULT_PRIVATE_CONFIG_FILE = REPO_ROOT / "config" / "clawqueue.private.json"
DEFAULT_PROFILES_DIR = REPO_ROOT / "profiles"
DEFAULT_REPO_CONFIG_FILE = REPO_ROOT / ".clawqueue" / "config.yaml"




class ConfigError(RuntimeError):
    """Configuration is ambiguous or invalid enough that CQ should stop."""


def _split_scalar(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    if value[0:1] in {"'", '"'} and value[-1:] == value[0]:
        return value[1:-1]
    return value.split("#", 1)[0].strip()


def _load_repo_config(path: Path = DEFAULT_REPO_CONFIG_FILE) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        _warn(f"could not read repo config {path}: {exc}")
        return {}

    if path.suffix.lower() == ".json":
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            _warn(f"repo config {path} is not valid JSON: {exc}")
            return {}
        return data if isinstance(data, dict) else {}

    data: dict[str, Any] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        if key:
            data[key] = _split_scalar(value)
    return data


def _profile_dirs(profiles_dir: Path = DEFAULT_PROFILES_DIR) -> dict[str, Path]:
    if not profiles_dir.exists():
        return {}
    result: dict[str, Path] = {}
    for child in sorted(profiles_dir.iterdir()):
        if not child.is_dir() or child.name.startswith(".") or child.name == "__pycache__":
            continue
        result[child.name] = child
    return result


def resolve_profile(selected: str | None = None) -> tuple[str | None, Path | None]:
    """Resolve the active profile.

    Precedence: explicit argument (CLI), CLAWQUEUE_PROFILE, .clawqueue/config.yaml,
    auto-select exactly one profile, then error if multiple profiles are present.
    """
    profiles_dir = _config_path(os.environ.get("CLAWQUEUE_PROFILES_DIR", DEFAULT_PROFILES_DIR))
    profiles = _profile_dirs(profiles_dir)

    raw = (selected or os.environ.get("CLAWQUEUE_PROFILE") or "").strip()
    if not raw:
        raw = str(_load_repo_config().get("profile") or "").strip()

    if raw:
        if raw not in profiles:
            available = ", ".join(profiles) or "none"
            raise ConfigError(
                f"ClawQueue profile {raw!r} was selected but not found under {profiles_dir}. "
                f"Available profiles: {available}."
            )
        return raw, profiles[raw]

    if not profiles:
        return None, None
    if len(profiles) == 1:
        name, path = next(iter(profiles.items()))
        return name, path

    names = ", ".join(profiles)
    raise ConfigError(
        "Multiple ClawQueue profiles found: "
        f"{names}. Choose one with `python3 scripts/scheduler.py --profile <name>`, "
        "set `CLAWQUEUE_PROFILE=<name>`, or add `profile: <name>` to .clawqueue/config.yaml."
    )


def _warn(message: str) -> None:
    print(f"Config warning: {message}", file=sys.stderr)


def _env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        _warn(f"{name}={value!r} is not an integer; using {default}")
        return default


def _env_json_object(name: str) -> dict[str, Any]:
    value = os.environ.get(name)
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        _warn(f"{name} is not valid JSON: {exc}")
        return {}
    if not isinstance(parsed, dict):
        _warn(f"{name} must be a JSON object; ignoring {type(parsed).__name__}")
        return {}
    return parsed


def _config_path(value: Any) -> Path:
    return Path(os.path.expandvars(str(value))).expanduser()


def _load_json_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        _warn(f"could not read {path}: {exc}")
        return {}
    except json.JSONDecodeError as exc:
        _warn(f"{path} is not valid JSON: {exc}")
        return {}
    if not isinstance(data, dict):
        _warn(f"{path} must contain a JSON object; ignoring {type(data).__name__}")
        return {}
    return data


def _load_frontmatter(path: Path) -> dict[str, Any]:
    if not path.exists():
        _warn(f"policy file not found: {path}")
        return {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        _warn(f"could not read policy file {path}: {exc}")
        return {}
    if not text.startswith("---\n"):
        _warn(f"policy file {path} has no JSON frontmatter")
        return {}
    end = text.find("\n---", 4)
    if end == -1:
        _warn(f"policy file {path} has unterminated JSON frontmatter")
        return {}
    try:
        data = json.loads(text[4:end].strip())
    except json.JSONDecodeError as exc:
        _warn(f"policy frontmatter in {path} is not valid JSON: {exc}")
        return {}
    if not isinstance(data, dict):
        _warn(f"policy frontmatter in {path} must be a JSON object")
        return {}
    return data


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        existing = merged.get(key)
        if isinstance(existing, dict) and isinstance(value, dict):
            merged[key] = _deep_merge(existing, value)
        else:
            merged[key] = value
    return merged


@dataclass(frozen=True)
class ProjectConfig:
    name: str
    number: int
    repo: str
    project_id: Optional[str]
    field_id: Optional[str]
    status_options: dict[str, str]
    dispatch_statuses: tuple[str, ...] = ("Todo",)
    extra_repos: tuple[str, ...] = ()

    def status_name(self, status_key: str) -> str:
        return {
            "todo": "Todo",
            "in_progress": "In Progress",
            "review": "Review",
            "done": "Done",
        }.get(status_key, status_key.replace("_", " ").title())


@dataclass(frozen=True)
class RuntimeConfig:
    profile_name: Optional[str]
    profile_dir: Optional[Path]
    policy_file: Path
    private_config_file: Path
    sessions_dir: Path
    state_dir: Path
    shared_state_root: Path
    lock_file: Path
    last_run_file: Path
    active_file: Path
    attempt_count_file: Path
    command_ledger_file: Path
    log_dir: Path
    decision_log_file: Path
    decision_log_retention_days: int
    tg_ask_cooldown_file: Path
    last_telegram_target_file: Path
    tg_ask_cooldown_min: int
    user_active_gate_min: int
    max_attempts_per_issue: int
    min_run_interval_min: int
    idle_timeout_min: int
    day_stop_remaining_pct: int
    night_stop_remaining_pct: int
    daily_warn_remaining_pct: int
    weekly_warn_remaining_pct: int
    weekly_stop_remaining_pct: int
    night_hours: tuple[int, int]
    athens_utc_offset_hours: int
    taskboard_repo: str
    extra_repos: tuple[str, ...]
    modes_dir: Path
    modes_base_url: str
    all_opus: bool
    mode_priority: tuple[str, ...]
    analyst_modes: tuple[str, ...]
    mode_to_agent: dict[str, str]
    agent_roles: dict[str, tuple[str, ...]]
    agent_provider: dict[str, str]
    agent_fallback: dict[str, str]
    runner_backend: str  # "openclaw" | "claudecode" | "codex" | "antigravity" | "antigravity-gui"
    artifact_backend: str  # "local" | "git"
    artifact_repo: str
    artifact_checkout_dir: Path
    artifact_path: str
    artifact_commit: bool
    deliver_channel: str
    completion_notify_channel: str
    completion_notify_target: str
    openclaw_command: str
    github_assignee: Optional[str]
    reviewer_auto_closes_issue: bool
    change_author_allowlist: tuple[str, ...]
    telegram_bot_token: Optional[str]
    telegram_chat_id: Optional[str]
    projects: dict[str, ProjectConfig]
    project_routing_keywords: dict[str, tuple[str, ...]]

    def all_issue_repos(self) -> list[str]:
        project_repos: list[str] = []
        for project in self.projects.values():
            project_repos.append(project.repo)
            project_repos.extend(project.extra_repos)
        ordered = [self.taskboard_repo, *self.extra_repos, *project_repos]
        seen: set[str] = set()
        result: list[str] = []
        for repo in ordered:
            if repo and repo not in seen:
                seen.add(repo)
                result.append(repo)
        return result

    def resolve_agent_candidates(self, mode_label: str, explicit_agent: str | None = None) -> tuple[str, ...]:
        if explicit_agent:
            agent = explicit_agent.strip().lower()
            return (agent,) if agent else ()
        role = mode_label.strip().lower()
        candidates = tuple(agent for agent in self.agent_roles.get(role, ()) if agent)
        if candidates:
            return candidates
        default_agent = (self.mode_to_agent.get(role) or "").strip().lower()
        return (default_agent,) if default_agent else ()


def _build_agent_maps(all_opus: bool) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    if all_opus:
        mode_to_agent = {
            "ceo": "ceo",
            "cto": "ceo",
            "dev": "ceo",
            "engineer": "ceo",
            "cmo": "cmo",
            "researcher": "researcher",
            "reviewer": "reviewer",
        }
        agent_provider = {
            "ceo": "codex",
            "cmo": "codex",
            "researcher": "codex",
            "reviewer": "codex",
        }
        agent_fallback = {
            "ceo": "cto",
            "reviewer": "cmo",
        }
        return mode_to_agent, agent_provider, agent_fallback

    mode_to_agent = {
        "ceo": "ceo",
        "cto": "cto",
        "dev": "dev",
        "engineer": "dev",
        "cmo": "cmo",
        "researcher": "researcher",
        "reviewer": "reviewer",
    }
    agent_provider = {
        "ceo": "codex",
        "cto": "codex",
        "dev": "codex",
        "cmo": "codex",
        "researcher": "codex",
        "reviewer": "codex",
    }
    agent_fallback = {
        "ceo": "cto",
        "reviewer": "cmo",
        "cto": "ceo",
        "cmo": "reviewer",
        "researcher": "cto",
    }
    return mode_to_agent, agent_provider, agent_fallback


def _path_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-._")
    return slug or "unknown"


def _string_map(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {str(k): str(v) for k, v in value.items() if str(k) and str(v)}


def _string_list_map(value: Any) -> dict[str, tuple[str, ...]]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, tuple[str, ...]] = {}
    for key, raw in value.items():
        role = str(key).strip()
        if not role:
            continue
        if isinstance(raw, str):
            items = [raw]
        elif isinstance(raw, (list, tuple)):
            items = list(raw)
        else:
            continue
        candidates = tuple(str(item).strip() for item in items if str(item).strip())
        if candidates:
            result[role] = candidates
    return result


def _project_from_dict(name: str, data: dict[str, Any], default_repo: str) -> ProjectConfig:
    status_options = data.get("status_options") or {}
    dispatch_statuses = data.get("dispatch_statuses", ["Todo"])
    if isinstance(dispatch_statuses, str):
        dispatch_statuses = [dispatch_statuses]
    if not isinstance(dispatch_statuses, list):
        dispatch_statuses = ["Todo"]
    return ProjectConfig(
        name=name,
        number=int(data.get("number", 0)),
        repo=str(data.get("repo") or default_repo),
        project_id=data.get("project_id"),
        field_id=data.get("field_id"),
        status_options={str(k): str(v) for k, v in status_options.items() if v},
        dispatch_statuses=tuple(str(item) for item in dispatch_statuses if str(item).strip()),
        extra_repos=tuple(str(item) for item in data.get("extra_repos", []) if item),
    )


def load_config(profile: str | None = None) -> RuntimeConfig:
    explicit_policy = os.environ.get("CLAWQUEUE_POLICY_FILE")
    profile_name, profile_dir = resolve_profile(profile) if not explicit_policy else (profile, None)
    default_policy_file = (profile_dir / "config" / "workflow_policy.md") if profile_dir else DEFAULT_POLICY_FILE
    default_private_config_file = (
        (profile_dir / "config" / "clawqueue.private.json") if profile_dir else DEFAULT_PRIVATE_CONFIG_FILE
    )
    policy_file = _config_path(explicit_policy or default_policy_file)
    private_config_file = _config_path(
        os.environ.get("CLAWQUEUE_PRIVATE_CONFIG_FILE", default_private_config_file)
    )
    policy_data = _load_frontmatter(policy_file)
    private_data = _load_json_file(private_config_file)

    env_projects = _env_json_object("CLAWQUEUE_PROJECTS_JSON")

    merged = _deep_merge(policy_data, private_data)
    if env_projects:
        merged["projects"] = _deep_merge(merged.get("projects", {}), env_projects)

    openclaw_home = _config_path(
        os.environ.get("OPENCLAW_HOME", Path.home() / ".openclaw")
    )
    workspace = _config_path(
        os.environ.get("OPENCLAW_WORKSPACE", openclaw_home / "workspace")
    )

    runtime = merged.get("runtime", {})
    notifications = merged.get("notifications", {})
    routing = merged.get("routing", {})
    repositories = merged.get("repositories", {})
    github = merged.get("github", {})
    safety = merged.get("safety", {})
    activity = merged.get("activity", {})
    quota = merged.get("quota", {})
    projects_data = merged.get("projects", {})
    artifacts = merged.get("artifacts", {})

    state_dir = _config_path(
        os.environ.get(
            "CLAWQUEUE_STATE_DIR",
            runtime.get("state_dir")
            or (Path(tempfile.gettempdir()) / "clawqueue"),
        )
    )
    state_dir.mkdir(parents=True, exist_ok=True)

    log_dir = _config_path(
        os.environ.get(
            "CLAWQUEUE_LOG_DIR",
            runtime.get("log_dir")
            or (Path.home() / ".local" / "share" / "clawqueue"),
        )
    )
    log_dir.mkdir(parents=True, exist_ok=True)

    taskboard_repo = os.environ.get(
        "CLAWQUEUE_PRIMARY_REPO",
        repositories.get("primary", "example-org/clawqueue"),
    )
    default_shared_state_root = state_dir if state_dir.name == "clawqueue" else state_dir.parent
    shared_state_root = _config_path(
        os.environ.get(
            "CLAWQUEUE_SHARED_STATE_ROOT",
            runtime.get("shared_state_root") or default_shared_state_root,
        )
    )
    repo_state_key = _path_slug(taskboard_repo)
    for child in ("locks", "active", "attempts", "commands", "last-run"):
        (shared_state_root / child).mkdir(parents=True, exist_ok=True)
    extra_repos_raw = os.environ.get("CLAWQUEUE_EXTRA_REPOS")
    if extra_repos_raw:
        extra_repos = tuple(
            repo.strip() for repo in extra_repos_raw.split(",") if repo.strip()
        )
    else:
        extra_repos = tuple(
            str(repo) for repo in repositories.get("extras", []) if str(repo).strip()
        )

    all_opus = _env_bool(
        "CLAWQUEUE_ALL_OPUS",
        bool(runtime.get("all_opus", False)),
    )
    mode_to_agent, agent_provider, agent_fallback = _build_agent_maps(all_opus)
    mode_to_agent.update(_string_map(routing.get("mode_to_agent")))
    mode_to_agent.update(_string_map(_env_json_object("CLAWQUEUE_MODE_TO_AGENT_JSON")))
    agent_roles = {
        mode.strip().lower(): (agent.strip().lower(),)
        for mode, agent in mode_to_agent.items()
        if mode.strip() and agent.strip()
    }
    agent_roles.update(
        {
            role.strip().lower(): tuple(agent.strip().lower() for agent in agents if agent.strip())
            for role, agents in _string_list_map(routing.get("agent_roles")).items()
        }
    )
    agent_roles.update(
        {
            role.strip().lower(): tuple(agent.strip().lower() for agent in agents if agent.strip())
            for role, agents in _string_list_map(_env_json_object("CLAWQUEUE_AGENT_ROLES_JSON")).items()
        }
    )
    agent_provider.update(_string_map(routing.get("agent_provider")))
    agent_provider.update(_string_map(_env_json_object("CLAWQUEUE_AGENT_PROVIDER_JSON")))
    agent_fallback.update(_string_map(routing.get("agent_fallback")))
    agent_fallback.update(_string_map(_env_json_object("CLAWQUEUE_AGENT_FALLBACK_JSON")))
    mode_to_agent = {
        mode.strip().lower(): agent.strip().lower()
        for mode, agent in mode_to_agent.items()
        if mode.strip() and agent.strip()
    }
    agent_provider = {
        agent.strip().lower(): provider.strip().lower()
        for agent, provider in agent_provider.items()
        if agent.strip() and provider.strip()
    }
    agent_fallback = {
        agent.strip().lower(): fallback.strip().lower()
        for agent, fallback in agent_fallback.items()
        if agent.strip() and fallback.strip()
    }

    default_modes_dir = (profile_dir / "modes") if profile_dir else (workspace / "modes")
    modes_dir = _config_path(
        os.environ.get(
            "CLAWQUEUE_MODES_DIR",
            runtime.get("modes_dir") or default_modes_dir,
        )
    )
    modes_base_url = os.environ.get(
        "CLAWQUEUE_MODES_BASE_URL",
        runtime.get("modes_base_url")
        or f"https://raw.githubusercontent.com/{taskboard_repo}/main/modes",
    )

    project_configs = {
        name: _project_from_dict(name, data, taskboard_repo)
        for name, data in projects_data.items()
        if isinstance(data, dict)
    }

    return RuntimeConfig(
        profile_name=profile_name,
        profile_dir=profile_dir,
        policy_file=policy_file,
        private_config_file=private_config_file,
        sessions_dir=Path(
            os.environ.get(
                "CLAWQUEUE_SESSIONS_DIR",
                runtime.get("sessions_dir") or (openclaw_home / "agents" / "main" / "sessions"),
            )
        ),
        state_dir=state_dir,
        shared_state_root=shared_state_root,
        lock_file=shared_state_root / "locks" / f"{repo_state_key}.lock",
        last_run_file=shared_state_root / "last-run" / f"{repo_state_key}",
        active_file=shared_state_root / "active" / f"{repo_state_key}.json",
        attempt_count_file=shared_state_root / "attempts" / f"{repo_state_key}.json",
        command_ledger_file=shared_state_root / "commands" / f"{repo_state_key}.json",
        log_dir=log_dir,
        decision_log_file=log_dir / "decisions.jsonl",
        decision_log_retention_days=_env_int(
            "CLAWQUEUE_DECISION_LOG_RETENTION_DAYS",
            int(runtime.get("decision_log_retention_days", 7)),
        ),
        tg_ask_cooldown_file=state_dir / "clawqueue_tg_asked",
        last_telegram_target_file=state_dir / "clawqueue_last_telegram_target",
        tg_ask_cooldown_min=_env_int(
            "CLAWQUEUE_TG_ASK_COOLDOWN_MIN",
            int(runtime.get("tg_ask_cooldown_min", 30)),
        ),
        user_active_gate_min=_env_int(
            "CLAWQUEUE_USER_ACTIVE_GATE_MIN",
            int(activity.get("user_active_gate_min", 0)),
        ),
        max_attempts_per_issue=_env_int(
            "CLAWQUEUE_MAX_ATTEMPTS_PER_ISSUE",
            int(runtime.get("max_attempts_per_issue", 5)),
        ),
        min_run_interval_min=_env_int(
            "CLAWQUEUE_MIN_RUN_INTERVAL_MIN",
            int(runtime.get("min_run_interval_min", 2)),
        ),
        idle_timeout_min=_env_int(
            "CLAWQUEUE_IDLE_TIMEOUT_MIN",
            int(runtime.get("idle_timeout_min", 0)),
        ),
        day_stop_remaining_pct=_env_int(
            "CLAWQUEUE_DAY_STOP_REMAINING_PCT",
            int(quota.get("daily_stop_remaining_pct", quota.get("day_stop_remaining_pct", 5))),
        ),
        night_stop_remaining_pct=_env_int(
            "CLAWQUEUE_NIGHT_STOP_REMAINING_PCT",
            int(quota.get("night_stop_remaining_pct", 5)),
        ),
        daily_warn_remaining_pct=_env_int(
            "CLAWQUEUE_DAILY_WARN_REMAINING_PCT",
            int(quota.get("daily_warn_remaining_pct", 10)),
        ),
        weekly_warn_remaining_pct=_env_int(
            "CLAWQUEUE_WEEKLY_WARN_REMAINING_PCT",
            int(quota.get("weekly_warn_remaining_pct", 20)),
        ),
        weekly_stop_remaining_pct=_env_int(
            "CLAWQUEUE_WEEKLY_STOP_REMAINING_PCT",
            int(quota.get("weekly_stop_remaining_pct", 0)),
        ),
        night_hours=tuple(quota.get("night_hours", [0, 0])),
        athens_utc_offset_hours=int(activity.get("athens_utc_offset_hours", 2)),
        taskboard_repo=taskboard_repo,
        extra_repos=extra_repos,
        modes_dir=modes_dir,
        modes_base_url=modes_base_url,
        all_opus=all_opus,
        mode_priority=tuple(
            routing.get(
                "mode_priority",
                ["ceo", "cto", "reviewer", "cmo", "researcher", "dev", "engineer"],
            )
        ),
        analyst_modes=tuple(routing.get("analyst_modes", ["researcher"])),
        mode_to_agent=mode_to_agent,
        agent_roles=agent_roles,
        agent_provider=agent_provider,
        agent_fallback=agent_fallback,
        runner_backend=os.environ.get(
            "CLAWQUEUE_RUNNER_BACKEND",
            runtime.get("runner_backend", "openclaw"),
        ),
        artifact_backend=os.environ.get(
            "CLAWQUEUE_ARTIFACT_BACKEND",
            artifacts.get("backend", "local"),
        ).strip().lower(),
        artifact_repo=os.environ.get(
            "CLAWQUEUE_ARTIFACT_REPO",
            artifacts.get("repo", ""),
        ),
        artifact_checkout_dir=_config_path(
            os.environ.get(
                "CLAWQUEUE_ARTIFACT_CHECKOUT_DIR",
                artifacts.get("checkout_dir") or (REPO_ROOT.parent / "clawqueue-worklog"),
            )
        ),
        artifact_path=os.environ.get(
            "CLAWQUEUE_ARTIFACT_PATH",
            artifacts.get("path", ".clawqueue/boards"),
        ),
        artifact_commit=_env_bool(
            "CLAWQUEUE_ARTIFACT_COMMIT",
            bool(artifacts.get("commit", False)),
        ),
        deliver_channel=os.environ.get(
            "CLAWQUEUE_DELIVER_CHANNEL",
            notifications.get("deliver_channel", "telegram"),
        ),
        completion_notify_channel=os.environ.get(
            "CLAWQUEUE_COMPLETION_NOTIFY_CHANNEL",
            notifications.get("completion_notify_channel", ""),
        ),
        completion_notify_target=os.environ.get(
            "CLAWQUEUE_COMPLETION_NOTIFY_TARGET",
            notifications.get("completion_notify_target", ""),
        ),
        openclaw_command=os.environ.get(
            "CLAWQUEUE_OPENCLAW_COMMAND",
            runtime.get("openclaw_command", "openclaw"),
        ),
        github_assignee=os.environ.get(
            "CLAWQUEUE_GITHUB_ASSIGNEE",
            github.get("assignee"),
        ),
        reviewer_auto_closes_issue=_env_bool(
            "CLAWQUEUE_REVIEWER_AUTO_CLOSES_ISSUE",
            bool(github.get("reviewer_auto_closes_issue", True)),
        ),
        change_author_allowlist=tuple(
            author.strip().lower()
            for author in (
                os.environ.get("CLAWQUEUE_CHANGE_AUTHOR_ALLOWLIST", "").split(",")
                if os.environ.get("CLAWQUEUE_CHANGE_AUTHOR_ALLOWLIST")
                else safety.get("change_author_allowlist", github.get("change_author_allowlist", []))
            )
            if str(author).strip()
        ),
        telegram_bot_token=os.environ.get(
            "CLAWQUEUE_TELEGRAM_BOT_TOKEN",
            notifications.get("telegram_bot_token"),
        ),
        telegram_chat_id=os.environ.get(
            "CLAWQUEUE_TELEGRAM_CHAT_ID",
            notifications.get("telegram_chat_id"),
        ),
        projects=project_configs,
        project_routing_keywords={
            name: tuple(str(keyword) for keyword in values)
            for name, values in routing.get("project_routing_keywords", {}).items()
            if isinstance(values, list)
        },
    )
