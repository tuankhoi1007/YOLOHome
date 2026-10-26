# Phase 0 — Agent workflow

Requested 2026-10-26 by the owner: "create the same structure for this project" as the IELTStudy *Agent Workflow & Quality Control* playbook. Effort: `low` (docs and config, no runtime code). Plan stated in chat, no separate approval step requested.

## Plan

Map each IELTStudy file to its YOLOHome counterpart:

| IELTStudy | YOLOHome |
| --- | --- |
| `specs.md` | `User_Requirements.md` |
| `docs/ROADMAP.md`, `docs/plans/` | same paths |
| `openapi.yaml` + `ERD.md` | `docs/PROTOCOL.md` (serial lines + feed list) |
| `backend/CLAUDE.md` | `code/CLAUDE.md` |
| `docs/CLAUDE_CODE_GUIDE.md` + playbook | `docs/AGENT_WORKFLOW.md` (one file) |
| typecheck/lint/test | `py_compile` + stdlib `unittest` |
| Prettier hook | `.claude/hooks/check_py.py` (syntax check after edit) |
| staff tests with secrets | hardware runs, done by the owner |

## Outcome

- Added: `CLAUDE.md` (rewritten), `code/CLAUDE.md`, `docs/AGENT_WORKFLOW.md`, `docs/ROADMAP.md`, `docs/PROTOCOL.md` v0.1.0, `docs/FIGMA.md`, `.claude/settings.json`, `.claude/hooks/check_py.py`, `CLAUDE.local.md` (gitignored).
- Removed: `.ai/TASKS.md`, `.ai/DECISIONS.md`, `.ai/LOG.md`, `.ai/FIGMA.md` from the previous setup; their content moved into `docs/ROADMAP.md` and `docs/FIGMA.md`.
- Deviations: no formatter hook — no formatter is in `requirements.txt` and adding one needs approval; the hook checks syntax instead. `pytest` is not installed, so tests use `unittest` (D9).
- Verified: hook script run on a valid and a broken file; `settings.json` parses as JSON.
- Not verified: hook on Windows teammates' machines (it calls `python3`).
- Left open: D3–D9 in the ROADMAP; Gate 0 approval. Work was done on `main` and is not committed.
