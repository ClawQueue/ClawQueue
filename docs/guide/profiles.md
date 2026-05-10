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
  secrets/        # ignored/private
```

For public repositories, keep the included profiles generic. Real customer,
company, or operator-specific profiles should live in a private repo or ignored
local folder.


For fuller profile conventions in the repository itself, see `profiles/README.md`.
