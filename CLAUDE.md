# CLAUDE.md

How Claude Code works on YOLOHome. The full way of working is in `docs/AGENT_WORKFLOW.md`; this file holds the rules that apply in every session. When this file and the chat disagree, this file wins.

## Project

- One-room smart home on OhStem Yolo:Bit, HK261 group 1 (CO3107). The laptop is the IoT gateway: USB serial ↔ Adafruit IO over MQTT. Face recognition and voice run on the laptop, never on the board.
- `README.md` says what already runs and how. Read it before touching `code/`.
- Python conventions for `code/` are in `code/CLAUDE.md`.

## Sources of truth

| Question | File | Who changes it |
| --- | --- | --- |
| What do we build? | `User_Requirements.md` | Owner only |
| What's next, is it done, what was decided? | `docs/ROADMAP.md` | Agent ticks after verification |
| How was a task planned, what happened? | `docs/plans/phase-<N>-<slug>.md` | Agent, kept current |
| What do board, gateway and dashboard send each other? | `docs/PROTOCOL.md` | Agent proposes, owner approves |
| Which Figma frame is which screen? | `docs/FIGMA.md` | Agent |
| How is gateway/board code written? | `code/CLAUDE.md` | Agent, when a new pattern lands |
| What may the agent run or touch? | `.claude/settings.json`, `.claude/hooks/` | Owner |

## Working rules

1. One ROADMAP task per session, on a feature branch, never on `main`. If the session starts on `main`, say so before editing.
2. At the start of a task, propose an effort level per subtask (one line each, with a reason). Ask the owner to run `/effort <level>` before a subtask that needs a higher level than the current one.
3. Anything beyond a small fix starts in plan mode. Edit nothing until the owner approves. Export the approved plan the same day to `docs/plans/phase-<N>-<slug>.md` with approval date and effort.
4. Build only what `User_Requirements.md` asks for. A gap or unclear point becomes a question, never an added feature. Open rows in the ROADMAP Decisions table are the owner's to answer.
5. Contract first: a change to serial commands, feed keys or thresholds goes into `docs/PROTOCOL.md` and is approved before code depends on it.
6. A fix that fails twice: stop, propose one effort level higher and a new plan. No third retry.
7. Done means the Definition of done in `docs/AGENT_WORKFLOW.md`. Say plainly what was not verified, especially anything that needs the board, the COM port or `.env`. Those runs are the owner's.
8. End each task with a one-line handoff prompt for the next session.

## Hard limits

- Never read, print or edit any `.env`. Key names are in `code/.env.example`.
- Never run `code/yolobit.py` on the laptop. It is MicroPython for the board.
- Do not edit `code/board_main_backup.py` (old prototype, reference only).
- Pins: P0 = light sensor, P14 = 4 RGB LEDs. Nothing else goes on them.
- Adafruit free tier: max 10 feeds, about 30 data points per minute in total. A plan that adds a feed or changes publish timing states the new feed count and points per minute.
- No LLM for voice, no native app, no AI on the board, no pump, soil or ultrasonic sensors.
- The door must stay openable from the UI when face recognition fails.

## Figma

Design file DADN, fileKey `capP3RVGqyp3EogAk90l6a`. The account has a View seat, so MCP calls are rate-limited: query single frames from `docs/FIGMA.md`, never the whole page. Figma output is a reference to adapt, not code to paste. Read-only unless a task says otherwise.
