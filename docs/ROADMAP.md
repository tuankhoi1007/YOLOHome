# Roadmap

One task per session. `[x]` only after the checks in `docs/AGENT_WORKFLOW.md` passed and the Outcome is written in `docs/plans/`. A phase starts only after the previous **Gate** is approved by the owner.

Effort in brackets is the suggested plan level; the agent re-proposes per subtask at task start.

## Phase 0 — Agent workflow

- [x] 0.1 Set up workflow files: `CLAUDE.md`, `code/CLAUDE.md`, `docs/`, `.claude/settings.json`, hook `[low]` → `plans/phase-0-agent-workflow.md`
- [ ] **Gate 0:** owner reads `docs/AGENT_WORKFLOW.md` and approves the structure.

## Phase 1 — Module 1–2 baseline (running, needs tests)

- [ ] 1.1 Add `code/tests/` with stdlib `unittest` for `parse_line`, `normalize_light`, `Reading.update`, `evaluate`, `Thresholds.apply_feed`. No serial, no network, fake env. `[medium]`
- [ ] 1.2 Owner re-runs `code/HUONG_DAN.md` end to end on hardware; agent records the result in the Outcome. `[low]`
- [ ] **Gate 1:** tests green, hardware loop confirmed, `PROTOCOL.md` v0.1.0 matches the code.

## Phase 2 — Module 3 contract

- [ ] 2.1 Settle D3, D4 (below) with the owner. `[high]`
- [ ] 2.2 Propose `PROTOCOL.md` v0.2.0: feeds `den`, `quat`, `cua`, serial commands for light/fan/servo, acknowledgements, feed budget and points/min. `[xhigh]`
- [ ] **Gate 2:** owner approves `PROTOCOL.md` v0.2.0. No Module 3 code before this.

## Phase 3 — Module 3 device control

- [ ] 3.1 `config.py` + `.env.example`: new feed constants. `[low]`
- [ ] 3.2 `gateway.py`: subscribe to control feeds, forward commands to serial, avoid echo loops. `[high]`
- [ ] 3.3 `yolobit.py`: handle new commands, fan and servo, keep alert LED behaviour per D3. `[high]`
- [ ] 3.4 Tests for command parsing and routing. `[medium]`
- [ ] **Gate 3:** owner demo on hardware: dashboard click → device reacts in < 3 s.

## Phase 4 — Module 4 log

- [ ] 4.1 Settle D5 (log storage). `[xhigh]`
- [ ] 4.2 Log device on/off, alerts and face attempts per D5. `[medium]`
- [ ] **Gate 4:** owner sees each event type in the log after a demo run.

## Phase 5 — Module 5 interface

- [ ] 5.1 Adafruit IO dashboard from the feeds in `PROTOCOL.md` (owner builds, agent writes the block list). `[low]`
- [ ] 5.2 Settle D6 (web stack, Adafruit auth); extract design tokens from Figma `180:20`. `[xhigh]`
- [ ] 5.3 Login screen from Figma `5:4`. `[medium]`
- [ ] 5.4 Dashboard normal / alert / offline from `11:593`, `11:1014`, `11:1418`, device states `181:10`, modal `28:1829`. `[medium]`
- [ ] 5.5 Activity log screen from `7:97` (needs Phase 4). `[medium]`
- [ ] **Gate 5:** works on phone and desktop width; sensor → screen < 5 s.

## Phase 6 — Face recognition (main AI)

- [ ] 6.1 Settle D7 (approach, library); plan dataset and internal test set. `[max]`
- [ ] 6.2 Enrol members, train, evaluate on the internal test set; record real accuracy. `[max]`
- [ ] 6.3 Correct face → servo opens door; wrong/failed → stays closed, UI button still works. `[high]`
- [ ] **Gate 6:** owner reviews the evaluation numbers and the fallback.

## Phase 7 — Vietnamese voice commands

- [ ] 7.1 Settle D8 (speech engine). `[high]`
- [ ] 7.2 Fixed commands for light and fan on/off, no LLM. `[medium]`
- [ ] **Gate 7:** owner demo of each command.

## Phase 8 — Demo hardening

- [ ] 8.1 30-minute stability run without losing Adafruit; fix what breaks. `[high]`
- [ ] 8.2 `/security-review` at `xhigh` (keys in browser, `.env`, door control). `[xhigh]`
- [ ] 8.3 Update `Bao_cao_NhaThongMinh.md` with real results. `[medium]`
- [ ] **Gate 8:** demo-ready.

## Decisions

Open rows are the owner's to answer. The agent does not decide them, and does not re-open closed ones.

| # | Question | Status | Answer | Blocks |
| --- | --- | --- | --- | --- |
| D1 | Which Figma file and account? | Closed 2026-10-26 | Account `pnghia`, file DADN `capP3RVGqyp3EogAk90l6a`, not the copy | — |
| D2 | Where does AI run? | Closed (spec) | Laptop gateway, webcam and mic of the laptop; never on the board | — |
| D3 | Share the 4 RGB LEDs on P14 between the alert (Module 2) and the manual light (Module 3), or move the alert to the 5x5 matrix only? | Open | | Phase 2 |
| D4 | Which ports for the fan relay and the servo? (Not P0, not P14.) | Open | | Phase 2 |
| D5 | Where is the Module 4 log stored? Feeds are 10/10 after Module 3. | Open | | Phase 4 |
| D6 | Web stack, and how does the browser control Adafruit without exposing `AIO_KEY`? | Open | | Phase 5 web |
| D7 | Face recognition approach and library. | Open | | Phase 6 |
| D8 | Vietnamese speech engine (offline or online). | Open | | Phase 7 |
| D9 | Test framework: stdlib `unittest`, no new dependency. | Proposed | | 1.1 |
