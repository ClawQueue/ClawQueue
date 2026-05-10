# Profiles

Profiles let ClawQueue stay generic while each deployment keeps its own company,
project, or contribution context.

A profile can define:

- company/project context
- agent identities
- mode prompts
- routing policy
- private config examples
- board guidance

Recommended shape:

```text
profiles/<name>/
  COMPANY.md
  PRODUCT_CONTEXT.md
  agents/
  modes/
  config/
    workflow_policy.md              # tracked/shared policy
    clawqueue.private.example.json  # safe template
    clawqueue.private.json          # ignored/per-user overrides
  secrets/                         # ignored/private
```

For public repositories, keep the included profiles generic. Real customer,
company, or operator-specific profiles should live in a private repo or ignored
local folder.

For shared profiles, select the profile by name:

```bash
python3 scripts/status.py --profile <name>
python3 scripts/scheduler.py --profile <name>
python3 scripts/install_launchd.py --repo "$HOME/ClawQueue" --profile <name>
```

Do not bake one user's checkout path or local OpenClaw agent IDs into tracked policy. Put those in ignored `profiles/<name>/config/clawqueue.private.json` or environment variables.

For fuller profile conventions in the repository itself, see `profiles/README.md`.
