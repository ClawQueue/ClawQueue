from __future__ import annotations

import importlib.util
import plistlib
import subprocess
import sys
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "install_launchd.py"


def load_installer():
    spec = importlib.util.spec_from_file_location("install_launchd", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_repo(root: Path) -> Path:
    repo = root / "repo"
    (repo / "config").mkdir(parents=True)
    (repo / "config" / "company_workflow_policy.md").write_text("---\n{}\n---\n", encoding="utf-8")
    return repo


def run_installer(monkeypatch, tmp_path: Path, args: list[str]):
    installer = load_installer()
    home = tmp_path / "home"
    home.mkdir()
    calls: list[list[str]] = []

    def fake_run(cmd, check):
        calls.append(list(cmd))
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(sys, "argv", ["install_launchd.py", *args])

    assert installer.main() == 0
    return home, calls


def test_installer_exports_per_label_state_log_and_private_config(monkeypatch, tmp_path):
    repo = make_repo(tmp_path)
    private_config = repo / "config" / "clawqueue.private.json"
    private_config.write_text("{}", encoding="utf-8")

    home, calls = run_installer(
        monkeypatch,
        tmp_path,
        ["--repo", str(repo), "--label", "com.example.alpha"],
    )

    wrapper = home / ".openclaw" / "service-env" / "clawqueue-scheduler.sh"
    text = wrapper.read_text(encoding="utf-8")
    assert f"export CLAWQUEUE_PRIVATE_CONFIG_FILE={private_config}" in text
    assert f"export CLAWQUEUE_STATE_DIR={home}/.openclaw/tmp/clawqueue/com.example.alpha" in text
    assert f"export CLAWQUEUE_LOG_DIR={home}/.local/share/clawqueue/com.example.alpha" in text
    assert f"export CLAWQUEUE_SHARED_STATE_ROOT={home}/.openclaw/tmp/clawqueue/com.example.alpha" in text
    assert "exec /usr/bin/python3 scripts/scheduler.py\n" in text

    plist_path = home / "Library" / "LaunchAgents" / "com.example.alpha.plist"
    plist = plistlib.loads(plist_path.read_bytes())
    assert plist["StandardOutPath"] == f"{home}/.local/share/clawqueue/com.example.alpha/com.example.alpha.stdout.log"
    assert plist["StandardErrorPath"] == f"{home}/.local/share/clawqueue/com.example.alpha/com.example.alpha.stderr.log"
    assert calls[0][:2] == ["plutil", "-lint"]


def test_explicit_policy_derives_sibling_private_config(monkeypatch, tmp_path):
    repo = make_repo(tmp_path)
    profile_config = repo / "profiles" / "weatherxm" / "config"
    profile_config.mkdir(parents=True)
    policy = profile_config / "custom_policy.md"
    private_config = profile_config / "clawqueue.private.json"
    policy.write_text("---\n{}\n---\n", encoding="utf-8")

    home, _ = run_installer(
        monkeypatch,
        tmp_path,
        ["--repo", str(repo), "--policy", str(policy), "--label", "com.example.weatherxm"],
    )

    text = (home / ".openclaw" / "service-env" / "clawqueue-scheduler.sh").read_text(encoding="utf-8")
    assert f"export CLAWQUEUE_POLICY_FILE={policy}" in text
    assert f"export CLAWQUEUE_PRIVATE_CONFIG_FILE={private_config}" in text


def test_custom_state_log_and_private_config_paths(monkeypatch, tmp_path):
    repo = make_repo(tmp_path)
    private_config = repo / "private" / "cq.json"
    private_config.parent.mkdir()
    private_config.write_text("{}", encoding="utf-8")

    home, _ = run_installer(
        monkeypatch,
        tmp_path,
        [
            "--repo",
            str(repo),
            "--private-config",
            "private/cq.json",
            "--state-dir",
            "runtime/state",
            "--log-dir",
            "runtime/logs",
            "--label",
            "com.example.custom",
        ],
    )

    text = (home / ".openclaw" / "service-env" / "clawqueue-scheduler.sh").read_text(encoding="utf-8")
    assert f"export CLAWQUEUE_PRIVATE_CONFIG_FILE={private_config}" in text
    assert f"export CLAWQUEUE_STATE_DIR={repo}/runtime/state" in text
    assert f"export CLAWQUEUE_LOG_DIR={repo}/runtime/logs" in text
    assert f"export CLAWQUEUE_SHARED_STATE_ROOT={repo}/runtime/state" in text
    assert (repo / "runtime" / "state").is_dir()
    assert (repo / "runtime" / "logs").is_dir()
