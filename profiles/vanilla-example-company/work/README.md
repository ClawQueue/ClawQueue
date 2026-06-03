# Vanilla Example Work Guidance

This folder is for optional hand-authored board guidance only, not generated deliverables.

Generated ClawQueue artifacts default to ignored local state under `.clawqueue/boards`. Companies that want artifacts in git should create a second repo dedicated to worklog/artifacts and configure:

```json
"artifacts": {
  "backend": "git",
  "repo": "your-org/clawqueue-worklog",
  "path": "boards",
  "commit": true
}
```

See `../../../docs/guide/artifacts.md`.
