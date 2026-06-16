#!/usr/bin/env python3
"""ClawQueue helper script to run a task using Google Antigravity 2.0.

This script acts as a bridge:
1. It connects to the running AG2R client (https://github.com/the-future-company/ag2r) on port 3000.
2. It injects the ClawQueue prompt into the Antigravity desktop app via CDP.
3. It polls the session snapshot status to keep the ClawQueue background PID alive.
4. It exits with 0 once the Antigravity agent finishes executing.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error
from http.cookiejar import CookieJar
from pathlib import Path

# Common paths
AG2R_DIR = Path("/Users/manos/Code/ag2r")


def load_ag2r_env() -> dict[str, str]:
    """Load configuration from AG2R .env file."""
    config = {
        "PORT": "3000",
        "AUTH_ENABLED": "false",
        "APP_PASSWORD": "antigravity",
    }
    env_path = AG2R_DIR / ".env"
    if not env_path.exists():
        return config

    try:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                config[key.strip()] = val.strip().strip('"').strip("'")
    except Exception as exc:
        print(f"⚠️ Warning: Could not parse AG2R .env: {exc}", file=sys.stderr)

    return config


def main() -> int:
    import ssl
    parser = argparse.ArgumentParser(description="Antigravity 2.0 GUI Runner Bridge for ClawQueue")
    parser.add_argument("--prompt", required=True, help="The task prompt to inject")
    args = parser.parse_args()

    config = load_ag2r_env()
    port = config["PORT"]
    auth_enabled = config["AUTH_ENABLED"].lower() == "true"
    password = config["APP_PASSWORD"]
    base_url = f"https://localhost:{port}"

    # Setup SSL context to ignore self-signed cert warnings
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    # Setup CookieJar and HTTP Opener for maintaining auth session
    cj = CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    urllib.request.install_opener(opener)

    print(f"🤖 Antigravity GUI Runner: Connecting to AG2R on {base_url}...")

    # 1. If auth is enabled, log in first
    if auth_enabled:
        print("🔑 Authentication is enabled in AG2R. Logging in...")
        login_url = f"{base_url}/login"
        login_data = json.dumps({"password": password}).encode("utf-8")
        req = urllib.request.Request(
            login_url,
            data=login_data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, context=ssl_context) as resp:
                res_body = json.loads(resp.read().decode("utf-8"))
                if not res_body.get("ok"):
                    print("❌ Login failed: AG2R rejected the password.", file=sys.stderr)
                    return 1
                print("✅ Successfully authenticated with AG2R.")
        except urllib.error.URLError as exc:
            print(f"❌ Could not connect to AG2R at {login_url}: {exc}", file=sys.stderr)
            print("💡 Please make sure AG2R is running (`node server.js` in /Users/manos/Code/ag2r).", file=sys.stderr)
            print("💡 Also ensure the Antigravity desktop app is open with CDP enabled on port 9000.", file=sys.stderr)
            return 1

    # 1.5. Ensure the dedicated ClawQueue project is selected and reuse its latest session
    print("📁 Selecting the dedicated 'ClawQueue' project and reusing its session when available...")
    eval_url = f"{base_url}/eval"
    select_project_script = """
    (() => {
        const projectCards = document.querySelectorAll('[data-project-card="true"]');
        let cqCard = null;
        for (const card of projectCards) {
            if ((card.textContent || '').toLowerCase().includes('clawqueue')) {
                cqCard = card;
                break;
            }
        }
        if (!cqCard) return { ok: false, reason: 'cq_project_not_found' };
        
        // Expand the project row if it is not expanded
        if (cqCard.getAttribute('aria-expanded') !== 'true') {
            cqCard.click();
        }
        
        // Search only the current project's conversation rows, stopping at the next project card.
        const section = cqCard.parentElement;
        if (!section) return { ok: false, reason: 'cq_project_parent_missing' };

        const conversationRows = [];
        let sibling = cqCard.nextElementSibling;
        while (sibling) {
            if (sibling.matches('[data-project-card="true"]')) break;
            const row =
                sibling.querySelector('[data-testid^="convo-pill-"]')?.closest('[role="button"]') ||
                sibling.querySelector('[role="button"]');
            if (row && row.textContent && row.textContent.trim()) {
                conversationRows.push(row);
            }
            sibling = sibling.nextElementSibling;
        }

        if (conversationRows.length > 0) {
            // Reuse the latest visible conversation so all ClawQueue runs keep shared context.
            const existingConvo = conversationRows[0];
            existingConvo.click();
            return {
                ok: true,
                method: 'existing_conversation_reused',
                title: existingConvo.textContent.trim().substring(0, 80),
            };
        }
        
        // No conversation exists yet for this project, so create the initial one.
        const buttons = cqCard.querySelectorAll('button');
        let plusBtn = null;
        for (const btn of buttons) {
            const svg = btn.querySelector('svg');
            if (svg && svg.innerHTML.includes('M450-450')) {
                plusBtn = btn;
                break;
            }
        }
        
        if (!plusBtn && buttons.length >= 1) {
            plusBtn = buttons[buttons.length - 1];
        }
        
        if (plusBtn) {
            plusBtn.click();
            return { ok: true, method: 'plus_button_new_convo' };
        }
        
        cqCard.click();
        return { ok: true, method: 'card_click' };
    })()
    """
    eval_data = json.dumps({"script": select_project_script}).encode("utf-8")
    req = urllib.request.Request(
        eval_url,
        data=eval_data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, context=ssl_context) as resp:
            res_body = json.loads(resp.read().decode("utf-8"))
            result = res_body.get("result", {})
            if result and result.get("ok"):
                method = result.get("method")
                if method == "existing_conversation_reused":
                    print(f"✅ Reusing existing 'ClawQueue' conversation: {result.get('title', '(untitled)')}")
                elif method == "plus_button_new_convo":
                    print("✅ Created the initial conversation inside the 'ClawQueue' project.")
                else:
                    print(f"✅ Selected the 'ClawQueue' project (method: {method}).")
                # Wait briefly for the conversation view to render fully
                time.sleep(2)
            else:
                print(f"⚠️ Warning: Could not find or select 'ClawQueue' project folder: {result.get('reason', 'unknown')}. Falling back to active view.", file=sys.stderr)
    except Exception as exc:
        print(f"⚠️ Warning: Could not contact /eval endpoint to select project: {exc}. Proceeding with active view.", file=sys.stderr)

    # 2. Inject the prompt
    print("📤 Injecting ClawQueue task prompt into the Antigravity desktop app...")
    send_url = f"{base_url}/send"
    send_data = json.dumps({"message": args.prompt}).encode("utf-8")
    req = urllib.request.Request(
        send_url,
        data=send_data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, context=ssl_context) as resp:
            res_body = json.loads(resp.read().decode("utf-8"))
            if not res_body.get("ok") and res_body.get("reason") == "no_editor":
                print("❌ Injection failed: No active editor/chat window found in Antigravity.", file=sys.stderr)
                print("💡 Please make sure the Antigravity app has a project open and a chat window is visible.", file=sys.stderr)
                return 1
            print("🚀 Prompt successfully injected! Antigravity desktop app is now executing the task.")
    except urllib.error.URLError as exc:
        print(f"❌ Failed to send prompt to AG2R: {exc}", file=sys.stderr)
        return 1

    # 3. Poll the snapshot endpoint to monitor execution state
    print("👀 Monitoring execution progress. You can inspect the GUI live on your screen or via your AG2R phone/browser UI!")
    snapshot_url = f"{base_url}/snapshot"

    # Give the agent a few seconds to boot/parse and start thinking
    time.sleep(10)

    has_started = False
    consecutive_idle_ticks = 0

    while True:
        try:
            req = urllib.request.Request(snapshot_url, method="GET")
            with urllib.request.urlopen(req, context=ssl_context) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                is_running = data.get("agentRunning", False)
                html_content = data.get("html", "")

                # Detect if the task has completed via ClawQueue done marker in the Agent's actual response
                # (Ignore occurrences in the User prompt by searching only after 'Agent response')
                agent_response_idx = html_content.find('aria-label="Agent response"')
                if agent_response_idx != -1:
                    agent_html = html_content[agent_response_idx:]
                    if "clawqueue:done" in agent_html:
                        print("🎉 ClawQueue done marker (<!-- clawqueue:done -->) detected in the Antigravity agent response!")
                        print("✅ Task successfully completed!")
                        break

                # State machine tracking based on the "agentRunning" field
                if is_running:
                    if not has_started:
                        print("⚡ Antigravity agent has started thinking and execution...")
                        has_started = True
                    consecutive_idle_ticks = 0
                else:
                    if has_started:
                        consecutive_idle_ticks += 1
                        # If the agent has been idling for 3 consecutive poll ticks (15 seconds)
                        # and has started at some point, it likely completed or failed.
                        if consecutive_idle_ticks >= 3:
                            print("💤 Antigravity agent has stopped thinking (idle). Exiting bridge process.")
                            break

        except urllib.error.URLError as exc:
            print(f"⚠️ Warning: Connection lost or polling error: {exc}. Retrying in 5s...", file=sys.stderr)

        time.sleep(5)

    return 0


if __name__ == "__main__":
    sys.exit(main())
