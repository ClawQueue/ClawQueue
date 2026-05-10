# Artifacts

Generated reports, research briefs, and handoff notes should not pollute product
branches.

## Default

Use ignored local artifacts:

```json
{
  "artifacts": {
    "backend": "local",
    "path": ".clawqueue/boards",
    "commit": false
  }
}
```

## Worklog repo

Teams that want durable generated artifacts in git should use a second repo dedicated to worklog/artifacts:

```json
{
  "artifacts": {
    "backend": "git",
    "repo": "your-org/clawqueue-worklog",
    "path": "boards",
    "commit": true
  }
}
```

That keeps implementation PRs reviewable while preserving operational memory.
