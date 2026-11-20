# IELTStudy — Agent Workflow & Quality Control Playbook

Oct 26, 2026 · @phanqig

## Purpose and principles

The agent writes most of the code; I own the decisions, the gates and the final check. This playbook pulls together the rules spread across `CLAUDE.md`, `backend/CLAUDE.md`, `docs/CLAUDE_CODE_GUIDE.md`, `docs/ROADMAP.md`, `docs/plans/` and `.claude/settings.json` into one way of working.

Five principles carry everything else:

1. **Write the rule down once.** A rule in a repo file applies in every session and for every teammate. A rule said only in chat dies at `/clear`.
2. **Plan before code, approve before build.** Nothing beyond a small fix is edited until I approve a plan, and every approved plan is exported to `docs/plans/`.
3. **The spec is the boundary.** The agent builds what `specs.md` asks for and nothing more. Gaps and unclear points come back to me as questions, not as extra features.
4. **Verified, not claimed.** "Done" means typecheck, lint and tests passed in this session, and the Outcome note says what changed and what deviated.
5. **Fix the rule, not just the output.** When the agent repeats a mistake, I add a line to `CLAUDE.md` or `backend/CLAUDE.md` so it can't happen again.

## Sources of truth

Each question has exactly one file that answers it. When the agent and a file disagree, the file wins; when two files disagree, I fix the file.

| Question | File | Who changes it |
| --- | --- | --- |
| What do we build? | `specs.md` | Me only |
| What's next, and is it done? | `docs/ROADMAP.md` (tasks, gates, Decisions table) | Agent ticks, after verification |
| How was it planned, and what actually happened? | `docs/plans/phase-<N>-<slug>.md` (plan + Outcome per task) | Agent, kept current |
| What does the data look like, and which rules must the app enforce? | `docs/ERD.md` | Agent proposes, I approve |
| What does the API promise? | `backend/src/docs/openapi.yaml` | Same change as the endpoint |
| How does the agent behave on this project? | `CLAUDE.md` (root) | Me, or agent on request |
| How is backend code written? | `backend/CLAUDE.md` | Agent, when a new pattern lands |
| What may the agent run or touch? | `.claude/settings.json` + `.claude/hooks/` | Me |
| How do I steer the agent? | `docs/CLAUDE_CODE_GUIDE.md` and this playbook | Me |

The Decisions table in `ROADMAP.md` is where a choice made in chat becomes permanent. Open rows (recommender ranking, UI design) are questions the agent must not answer on its own.

## The task lifecycle

Every `ROADMAP.md` task follows the same loop, with two points where work stops until it passes: my plan approval and the automated checks.

&#91;embedded content: task lifecycle · 10 steps, 2 decisions, 1 phase gate\]

Checks means `npm run typecheck && npm run lint && npm test` (plus frontend build and e2e when the UI changed). After `/clear`, the next session starts again at "Pick next task".

## Controlling the agent

I control the agent with four levers: what it may do (permissions), how hard it thinks (effort), when it may start (plan approval and gates), and how far it may go (scope).

### 1. Permissions, enforced by the harness

These live in `.claude/settings.json`, so they hold even if the agent forgets an instruction.

| Level | What | Why |
| --- | --- | --- |
| Runs freely | `npm run *`, `npm install`, `npm test`, `tsc`, `prisma contract emit`, read-only git | Checks and builds are cheap and reversible |
| Asks me first | `git commit`, `git checkout`, `git reset`, `prisma db` / `migration`, `psql`, editing `schema.prisma` | Changes history, the database or the frozen schema |
| Blocked | `git push`, `rm -rf`, any read or write of `.env` | Outward-facing, destructive or secret |
| Automatic | Prettier on every edited `backend/` file (`.claude/hooks/format.mjs`) | Formatting never needs a review comment |

### 2. Effort per task and subtask

Effort matches how hard a task is to get *right*, not how big it is. At the start of every task the agent proposes a level per subtask, one line each with a reason, before any work begins.

| Level | Use for | Examples from this project |
| --- | --- | --- |
| `low` | Mechanical edits with a pattern to copy | ROADMAP tick, Outcome note, `.env.example`, a Joi field |
| `medium` | Standard features following a pattern | Admin roles and stats, supertest suites, seed data, pages |
| `high` | Cross-file rules that are easy to get subtly wrong | JWT + RBAC, course review flow, attempt submit in a transaction, signed uploads |
| `xhigh` | Decisions expensive to undo | Phase 1 schema, Phase 2 API contract, `/security-review` |
| `max` | Algorithms where a wrong answer looks plausible | BKT with Q-matrix split, recommender ranking, A/B metrics |

Rules I hold the agent to:

- Plan at the task's level, implement routine parts one level lower, tests at `medium`, docs at `low`.
- Before a subtask that needs a **higher** level, the agent stops and asks me to run `/effort <level>`. For a lower level it just mentions it.
- If the current level is two or more steps off, it says so before starting.
- A `low`/`medium` task that fails twice gets one level more and a new plan, not a third retry.

### 3. Plan approval and phase gates

- Anything beyond a small fix starts in **plan mode**: the agent researches and proposes, and edits nothing until I approve.
- The approved plan is exported the same day to `docs/plans/phase-<N>-<slug>.md` with its approval date and effort.
- Each phase ends at a **Gate** in `ROADMAP.md` that I approve before the next phase starts (e.g. "ERD reviewed, schema frozen", "API contract approved v0.2.0"). Contract-first: the OpenAPI contract was approved before any Phase 2 endpoint was built.
- Schema changes always need my approval: the agent proposes the `schema.prisma` change, then runs `contract:emit`.

### 4. Scope limits

- Build only what `specs.md` asks for. A missing or unclear point becomes a question to me, never an added feature.
- One `ROADMAP.md` task per session, on a feature branch, never on `main`.
- Every endpoint lives under `/api/v1` and goes into `openapi.yaml` in the same change.
- No new dependency without saying why; Prisma packages pinned exactly.
- Point at a reference ("follow `routes/me.ts`"): the agent copies existing patterns, so I keep the good ones clean.
- Code must stay readable for a 3rd-year CS student: plain TypeScript and Express, no type-level tricks or dense one-liners, comments on BKT, ranking and scoring logic.

## Quality checks

Quality is checked in three layers: automated gates the agent must pass, reviews run against the branch, and my own read of the result. A task is not done until all three hold.

### Layer 1: automated gates (agent runs, every task)

| Area | Command | What it proves |
| --- | --- | --- |
| Backend | `npm run typecheck && npm run lint && npm test` in `backend/` | Types, style, and supertest suites against a real Postgres (`TEST_DATABASE_URL`, wiped per test) |
| API contract | `npx @redocly/cli@1.34.5 lint src/docs/openapi.yaml` | Contract is valid; endpoints match the docs |
| Contract mocks | Prism on `openapi.yaml`, then `curl` a few routes | Examples and error shapes behave as written |
| Frontend | typecheck, lint, unit tests, `next build` | The UI compiles and mappers are tested |
| End to end | Playwright specs against the running backend | Each role's flow works in a browser |

Tests are the contract: "make these tests pass" gives the agent a way to verify itself; "make it work" doesn't. Tests that need secrets I hold (the staff spec and smoke scripts need `SEED_PASSWORD`) are run by me, and the Outcome says so.

### Layer 2: reviews (on the branch)

- `/code-review` at `high` or above for auth, scoring, BKT or recommender code; `medium` for the rest.
- A **review before each Gate**. Example: the review before the Phase 2 contract Gate found that approved courses' quizzes could be edited without re-review, and the contract was fixed before approval.
- `/security-review` at `xhigh` before deployment (Phase 7). Known security gaps, like the unchecked `mediaPath` owner, are logged in the Outcome and carried to that review.
- `/simplify` when code works but reads too clever for the readability rule.

### Layer 3: my own read

Before I accept a task I check:

- [ ] The diff matches the approved plan, or each deviation is explained in the Outcome.
- [ ] Nothing was built that `specs.md` doesn't ask for.
- [ ] Every new endpoint is under `/api/v1` and in `openapi.yaml`.
- [ ] Rules follow `backend/CLAUDE.md`: validated input from `req.value`, checks in order 404 → 403 → 409, `updateAndCount` for conditional updates, no `hashedPass` in responses, answers stay server-side.
- [ ] Non-obvious logic (BKT, ranking, scoring) has a plain-words comment.
- [ ] I can explain the change myself after reading the files the agent named.

### Definition of done

1. Typecheck, lint and tests pass, run in this session.
2. Task ticked in `ROADMAP.md`.
3. Outcome note written in `docs/plans/`: what changed, deviations and why, what is left open.
4. Chat-only decisions written to their file (`ERD.md`, `CLAUDE.md`, `backend/CLAUDE.md`, ROADMAP Decisions).
5. Work committed, or the agent reminds me to commit.

## Context and memory hygiene

Each `ROADMAP.md` task gets a fresh context, so the repo files, not the chat, carry the project forward.

- **`/clear` after every task**, not only at the end of a phase. Old context leaks assumptions into the next task.
- **`/compact` mid-task** when the session grows long, instead of clearing.
- **Before the agent suggests `/clear`**, it confirms the Definition of done above: ticked, Outcome written, checks green, chat decisions saved, work committed or a commit reminder given.
- **Where a chat decision goes:** schema rationale → `docs/ERD.md`; a new convention → `CLAUDE.md` or `backend/CLAUDE.md`; a product choice → the ROADMAP Decisions table; a plan change → its file in `docs/plans/`.
- **Personal preferences** (language, what I own) go in `CLAUDE.local.md`, which is gitignored, not in the shared `CLAUDE.md`.
- **Handoff prompt:** the agent ends each task with a one-line prompt for the next session, e.g. "Read `docs/ROADMAP.md` and start the next unticked task."

## Failure handling

When the agent goes off course, I stop it early and change the input (plan, effort or rule) rather than asking it to try again.

| Situation | What I do | Example from this project |
| --- | --- | --- |
| A fix fails twice or keeps changing | Stop; raise effort one level; re-plan | Rule in the Effort guide |
| The plan turns out wrong mid-task | Agent updates the plan file and names the deviation in the Outcome | Phase 4: mapping into UI types instead of replacing them, explained as a deviation |
| A request would go beyond the spec | Agent runs a gap analysis and asks; I decide | Phase 4: "fix the backend to fit the frontend" → no in-spec screen needed it, contract kept at v0.2.6 |
| A decision belongs to a later gate | Log it as "Left open" with the phase that settles it | Remedial-lesson access deferred to the Phase 3 Gate |
| A known risk is accepted for now | Record it in the Outcome and carry it to a named review | `mediaPath` owner check → Phase 7 security review |
| The agent repeats a mistake | Add a rule to `CLAUDE.md` / `backend/CLAUDE.md` | `.where().update()` isn't atomic → "use `updateAndCount`" |
| A test run finds a real bug | Fix it in the same task and note it in the Outcome | Playwright found "Enroll" clickable before auth loaded |
| Work I must do myself (secrets, `git rm`, commits) | Agent says so plainly; I run it with `! <command>` | Staff smoke tests with `SEED_PASSWORD` |

## Quick reference

### Prompt templates

- **Start a task:** "Read `docs/ROADMAP.md` and start the next unticked task. Suggest effort per subtask, then plan."
- **Point at a pattern:** "Follow the pattern in `backend/src/routes/me.ts` and `services/courses.ts`."
- **Make it verifiable:** "Write the supertest cases first, then make them pass."
- **Hold the scope:** "If `specs.md` doesn't cover something, list it as a question. Don't build it."
- **Explain back:** "What changed, why, and which files should I read to understand it?"
- **Lock a lesson in:** "Add a rule to `backend/CLAUDE.md` so this doesn't happen again."
- **Close a task:** "Run typecheck, lint and tests, write the Outcome, tick the ROADMAP, and tell me what to commit."

### Start-of-task checklist

- [ ] On a feature branch, not `main`
- [ ] Fresh context (`/clear` done after the last task)
- [ ] Effort suggested per subtask, and `/effort` set to the plan level
- [ ] Plan mode on for anything beyond a small fix
- [ ] Open Decisions that block this task are settled first

### End-of-task checklist

- [ ] `npm run typecheck && npm run lint && npm test` green
- [ ] `openapi.yaml` updated for any new endpoint
- [ ] Review run at the right level (auth, scoring, BKT, recommender: `high`+)
- [ ] Outcome note written, deviations explained
- [ ] `ROADMAP.md` ticked
- [ ] Chat decisions saved to their file
- [ ] Committed (I approve the commit; the agent never pushes)
- [ ] `/clear`, with the handoff prompt copied
