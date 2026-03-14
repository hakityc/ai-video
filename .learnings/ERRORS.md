# Errors

## [ERR-20260313-001] python command missing

**Logged**: 2026-03-13T00:00:00Z
**Priority**: medium
**Status**: resolved
**Area**: infra

### Summary
Local environment does not provide `python`; use `python3` for validation commands.

### Error
```
zsh:1: command not found: python
```

### Context
- Command/operation attempted: `python -m unittest discover -s tests`
- Environment detail: macOS shell in project workspace

### Suggested Fix
Prefer `python3` in local validation commands and add a project note if this environment is standard.

### Metadata
- Reproducible: yes
- Related Files: n/a
- Notes: Validation in this repo should use `python3` or `.venv/bin/python`.

### Resolution
- **Resolved**: 2026-03-13T00:00:00Z
- **Commit/PR**: working tree
- **Notes**: Switched validation commands to `.venv/bin/python` and `python3`.

---
