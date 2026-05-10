# Safety model

ClawQueue assumes a trusted operator on a trusted local machine.

It is not a hosted multi-tenant executor. It shells out to local tools, can start
agent processes, and uses local credentials configured by the operator.

## Rules of thumb

- Keep secrets out of tracked files.
- Use GitHub issues and PRs as the durable review surface.
- Keep generated artifacts out of product branches.
- Start with one worker at a time.
- Require human review before accepting external-facing work.
- Do not expose ClawQueue as a public service without authentication,
  authorization, sandboxing, auditing, and a real secret manager.
