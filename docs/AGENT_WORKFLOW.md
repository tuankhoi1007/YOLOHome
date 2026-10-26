# YOLOHome — Agent Workflow & Quality Control

Oct 26, 2026 · phanqig

## Purpose and principles

The agent writes most of the code; I own the decisions, the gates, the hardware runs and the final check. This playbook ties together `CLAUDE.md`, `code/CLAUDE.md`, `docs/ROADMAP.md`, `docs/PROTOCOL.md`, `docs/plans/` and `.claude/settings.json`.

1. **Write the rule down once.** A rule in a repo file applies in every session and for every teammate. A rule said only in chat dies at `/clear`.
2. **Plan before code, approve before build.** Nothing beyond a small fix is edited until I approve a plan, and every approved plan is exported to `docs/plans/`.
3. **The spec is the boundary.** The agent builds what `User_Requirements.md` asks for and nothing more. Gaps come back to me as questions, not as extra features.
4. **Verified, not claimed.** "Done" means the checks passed in this session, and the Outcome says what changed, what deviated, and what still needs the board.
5. **Fix the rule, not just the output.** When the agent repeats a mistake, I add a line to `CLAUDE.md` or `code/CLAUDE.md`.

## Sources of truth

Each question has one file that answers it. When the agent and a file disagree, the file wins; when two files disagree, I fix the file.

| Question | File | Who changes it |
| --- | --- | --- |
| What do we build? | `User_Requirements.md` | Me only (agent edits are blocked) |
| What's next, and is it done? | `docs/ROADMAP.md` (tasks, gates, Decisions table) | Agent ticks, after verification |
| How was it planned, what happened? | `docs/plans/phase-<N>-<slug>.md` (plan + Outcome) | Agent, kept current |
| What do board, gateway and dashboard send each other? | `docs/PROTOCOL.md` (serial lines, feed keys, thresholds, points/min) | Agent proposes, I approve (edits ask me) |
| Which Figma frame is which screen? | `docs/FIGMA.md` | Agent |
| What already runs and how to run it? | `README.md`, `code/HUONG_DAN.md` | Agent, in the same change as the code |
| How does the agent behave? | `CLAUDE.md` | Me, or agent on request |
| How is gateway/board code written? | `code/CLAUDE.md` | Agent, when a new pattern lands |
| What may the agent run or touch? | `.claude/settings.json` + `.claude/hooks/` | Me |
| How do I steer the agent? | this playbook | Me |

The Decisions table in `ROADMAP.md` is where a choice made in chat becomes permanent. Open rows (pin sharing, log storage, web stack, face library, speech engine) are questions the agent must not answer on its own.

## The task lifecycle

1. **Pick** the next unticked task in `ROADMAP.md`. Check that no open Decision blocks it.
2. **Effort:** the agent proposes a level per subtask; I set `/effort`.
3. **Plan** in plan mode: files, changes, feed count and points/min if feeds or timing change, what needs hardware.
4. **Decision — approve plan?** No → back to 3. Yes → plan exported to `docs/plans/`.
5. **Branch** off `main` (`feat/<phase>-<slug>`).
6. **Build**, following `code/CLAUDE.md`. The hook syntax-checks every edited `.py`.
7. **Checks** (Layer 1 below).
8. **Decision — checks green?** No → fix, at most twice, then raise effort and re-plan. Yes → continue.
9. **Hardware run** if the task touches serial, the board or Adafruit: I run it, the agent records the result.
10. **Close:** Outcome written, ROADMAP ticked, commit approved, `/clear` with the handoff prompt.

**Phase gate:** the last task of a phase is its Gate. I approve it before any task of the next phase starts.

## Controlling the agent

Four levers: what it may do (permissions), how hard it thinks (effort), when it may start (plan approval and gates), how far it may go (scope).

### 1. Permissions, enforced by the harness

In `.claude/settings.json`, so they hold even if the agent forgets an instruction.

| Level | What | Why |
| --- | --- | --- |
| Runs freely | `python3 -m py_compile`, `python3 -m unittest`, read-only git, Figma read tools | Checks are cheap and reversible |
| Asks me first | `git commit`, `checkout`, `switch`, `reset`, `stash`, `pip install`, `npm install`, editing `docs/PROTOCOL.md`, any Figma write | Changes history, dependencies, the contract or the shared design |
| Blocked | `git push`, `rm -rf`, any read or write of `.env`, editing `User_Requirements.md` or `board_main_backup.py` | Outward-facing, destructive, secret, or mine |
| Automatic | Syntax check on every edited `.py` (`.claude/hooks/check_py.py`); a syntax error is fed back to the agent | Broken files never reach a review |

Running `gateway.py`, `module1.py` or `module2.py` is not allowed by default: they need `.env`, the COM port and the network. Those are my runs.

### 2. Effort per task and subtask

Effort matches how hard a task is to get *right*, not how big it is. At the start of every task the agent proposes a level per subtask, one line each with a reason.

| Level | Use for | Examples from this project |
| --- | --- | --- |
| `low` | Mechanical edits with a pattern to copy | ROADMAP tick, Outcome note, `.env.example` line, a feed constant |
| `medium` | Standard work following a pattern | `unittest` suites, a new board command handler, a web page from a Figma frame, voice command table |
| `high` | Cross-file rules that are easy to get subtly wrong | Gateway routing feeds ↔ serial without echo loops, rate pacing, servo door with manual fallback, 30-min stability fixes |
| `xhigh` | Decisions expensive to undo | `PROTOCOL.md` v0.2.0 (feeds 10/10), log storage, web stack and Adafruit auth, `/security-review` |
| `max` | Algorithms where a wrong answer looks plausible | Face recognition model, match threshold, evaluation on the internal test set |

Rules:

- Plan at the task's level, implement routine parts one level lower, tests at `medium`, docs at `low`.
- Before a subtask that needs a **higher** level, the agent stops and asks me to run `/effort <level>`. For a lower level it just mentions it.
- If the current level is two or more steps off, it says so before starting.
- A `low`/`medium` task that fails twice gets one level more and a new plan, not a third retry.

### 3. Plan approval and phase gates

- Anything beyond a small fix starts in **plan mode**: the agent researches and proposes, and edits nothing until I approve.
- The approved plan is exported the same day to `docs/plans/phase-<N>-<slug>.md` with its approval date and effort.
- Each phase ends at a **Gate** in `ROADMAP.md` that I approve. Contract-first: `PROTOCOL.md` v0.2.0 (Gate 2) is approved before any Module 3 code.
- Any change to serial lines, feed keys, threshold meaning or publish timing goes through `PROTOCOL.md` first.

### 4. Scope limits

- Build only what `User_Requirements.md` asks for. Missing or unclear → question, never an added feature.
- One `ROADMAP.md` task per session, on a feature branch, never on `main`.
- No new dependency without saying why. Board code uses only what MicroPython on Yolo:Bit has.
- Point at a reference ("follow `SensorPublisher` in `module1.py`"): the agent copies existing patterns, so I keep the good ones clean.
- Code stays readable for a 3rd-year CS student: plain functions, small classes, comments on thresholds, timing and the face match logic.

## Quality checks

Three layers: automated gates the agent must pass, reviews on the branch, and my own read. A task is not done until all three hold.

### Layer 1: automated gates (agent runs, every task)

| Area | Command | What it proves |
| --- | --- | --- |
| Syntax | `python3 -m py_compile code/*.py` (and the hook per edit) | Every file parses, including `yolobit.py` |
| Unit tests | `python3 -m unittest discover -s code/tests -t code` (from ROADMAP 1.1) | Parsing, light scaling, threshold evaluation and command routing behave as `PROTOCOL.md` says, without serial or network |
| Contract | Agent diffs feed constants in `config.py` and commands in `yolobit.py` against `PROTOCOL.md` | Code and contract agree; feed count ≤ 10 |
| Web (Phase 5) | Build/lint of the chosen stack, checked at phone and desktop width | The UI compiles and fits both |
| Hardware | `code/HUONG_DAN.md` steps on the real board | **Mine.** The Outcome says "not hardware-verified" until I report back |

Tests are the contract: "make these tests pass" gives the agent a way to check itself; "make it work" doesn't.

### Layer 2: reviews (on the branch)

- `/code-review` at `high` or above for gateway routing, rate pacing, door/servo and face code; `medium` for the rest.
- A **review before each Gate**, against `PROTOCOL.md` and the spec.
- `/security-review` at `xhigh` before the demo (Phase 8): where `AIO_KEY` lives, what the web client can do, who can open the door.
- `/simplify` when code works but reads too clever for the readability rule.

### Layer 3: my own read

- [ ] The diff matches the approved plan, or each deviation is explained in the Outcome.
- [ ] Nothing was built that `User_Requirements.md` doesn't ask for.
- [ ] Serial lines and feeds match `PROTOCOL.md`; feed count ≤ 10; points/min stated if timing changed.
- [ ] P0 and P14 keep their roles; no AI on the board.
- [ ] Rules follow `code/CLAUDE.md`: settings via `config.py`, feeds as `FEED_*`, MQTT work through the queue, prints in unaccented Vietnamese.
- [ ] The door can still be opened from the UI when face recognition fails.
- [ ] I can explain the change myself after reading the files the agent named.

### Definition of done

1. Syntax check and unit tests pass, run in this session.
2. Hardware result recorded, or "not hardware-verified" stated.
3. Task ticked in `ROADMAP.md`.
4. Outcome written in `docs/plans/`: what changed, deviations and why, what is left open.
5. Chat decisions written to their file (`ROADMAP.md` Decisions, `PROTOCOL.md`, `CLAUDE.md`, `code/CLAUDE.md`).
6. `README.md` / `HUONG_DAN.md` updated if how to run it changed.
7. Work committed, or the agent reminds me to commit.

## Context and memory hygiene

- **`/clear` after every task.** Old context leaks assumptions into the next task.
- **`/compact` mid-task** when the session grows long, instead of clearing.
- **Before suggesting `/clear`**, the agent confirms the Definition of done.
- **Where a chat decision goes:** a protocol or feed change → `PROTOCOL.md`; a product choice → ROADMAP Decisions; a new convention → `CLAUDE.md` or `code/CLAUDE.md`; a plan change → its file in `docs/plans/`.
- **Personal preferences** go in `CLAUDE.local.md` (gitignored).
- **Handoff prompt:** each task ends with one line for the next session, e.g. "Read `docs/ROADMAP.md` and start the next unticked task."

## Failure handling

| Situation | What I do |
| --- | --- |
| A fix fails twice or keeps changing | Stop; raise effort one level; re-plan |
| The plan turns out wrong mid-task | Agent updates the plan file and names the deviation in the Outcome |
| A request would go beyond the spec | Agent runs a gap analysis against `User_Requirements.md` and asks; I decide |
| A decision belongs to a later gate | Log it as "Left open" with the phase that settles it |
| A known risk is accepted for now | Record it in the Outcome and carry it to the Phase 8 security review |
| The agent repeats a mistake | Add a rule to `CLAUDE.md` / `code/CLAUDE.md` |
| A hardware run finds a bug | Fix it in the same task and note it in the Outcome |
| Work I must do myself (`.env`, board, COM, commits, push) | Agent says so plainly; I run it, using `! <command>` when it's a shell command |

## Quick reference

### Prompt templates

- **Start a task:** "Read `docs/ROADMAP.md` and start the next unticked task. Suggest effort per subtask, then plan."
- **Point at a pattern:** "Follow `SensorPublisher` in `code/module1.py` and the queue in `code/gateway.py`."
- **Make it verifiable:** "Write the `unittest` cases first, then make them pass."
- **Hold the scope:** "If `User_Requirements.md` doesn't cover something, list it as a question. Don't build it."
- **Contract first:** "Propose the `PROTOCOL.md` change and the feed budget. No code yet."
- **Explain back:** "What changed, why, and which files should I read to understand it?"
- **Lock a lesson in:** "Add a rule to `code/CLAUDE.md` so this doesn't happen again."
- **Close a task:** "Run the checks, write the Outcome, tick the ROADMAP, and tell me what to commit and what to test on the board."

### Start-of-task checklist

- [ ] On a feature branch, not `main`
- [ ] Fresh context (`/clear` done after the last task)
- [ ] Effort suggested per subtask, `/effort` set to the plan level
- [ ] Plan mode on for anything beyond a small fix
- [ ] Open Decisions that block this task are settled

### End-of-task checklist

- [ ] `py_compile` and `unittest` green
- [ ] `PROTOCOL.md` updated and approved for any serial/feed change
- [ ] Review run at the right level (routing, pacing, door, face: `high`+)
- [ ] Hardware result recorded, or "not hardware-verified" stated
- [ ] Outcome written, deviations explained
- [ ] `ROADMAP.md` ticked
- [ ] Chat decisions saved to their file
- [ ] Committed (I approve the commit; the agent never pushes)
- [ ] `/clear`, with the handoff prompt copied
